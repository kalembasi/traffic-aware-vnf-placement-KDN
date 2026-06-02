import networkx as nx
import xgboost as xgb
import pickle
import random
from src.algorithms.base import BasePlacement
from src.sfc import VNF_REQUIREMENTS, SFC_CATALOG, SFC_BANDWIDTH

class XGBoostPlacement(BasePlacement):
    def __init__(self):
        # 1. Load trained XGBoost models (Two-Stage Architecture) and encoder mapping
        self.classifier = xgb.XGBClassifier()
        self.classifier.load_model('models/kdn_classifier.json')
        
        self.regressor = xgb.XGBRegressor()
        self.regressor.load_model('models/kdn_regressor.json')
        
        with open('models/label_encoder.pkl', 'rb') as f:
            self.encoder = pickle.load(f)

    def _get_network_state(self, graph):
        # Default node constraint
        max_cpu = 100.0  
        active_nodes = sum(1 for n in graph.nodes() if graph.nodes[n]['cpu_capacity'] < max_cpu)
        free_cpu = sum(graph.nodes[n]['cpu_capacity'] for n in graph.nodes())
        free_bw = sum(graph[u][v]['bandwidth'] for u, v in graph.edges())
        max_node_utilization = max([((max_cpu - graph.nodes[n]['cpu_capacity']) / max_cpu) * 100 for n in graph.nodes()]) if graph.nodes() else 0
        bottleneck_bw = min([graph[u][v]['bandwidth'] for u, v in graph.edges()]) if graph.edges() else 0
        return active_nodes, free_cpu, free_bw, max_node_utilization, bottleneck_bw

    def place_sfc(self, graph, sfc_name):
        chain = SFC_CATALOG[sfc_name]
        bw_demand = SFC_BANDWIDTH[sfc_name]
        
        # Capture strictly current graph baseline
        active_nodes, free_cpu, free_bw, max_node_utilization, bottleneck_bw = self._get_network_state(graph)
        sfc_type_encoded = self.encoder.transform([sfc_name])[0]
        state_array = [sfc_type_encoded, active_nodes, free_cpu, free_bw, max_node_utilization, bottleneck_bw]
        
        # --- Stage 1: The Gatekeeper (Classifier Admission Control) ---
        prediction = self.classifier.predict([state_array])[0] # Will return 0 or 1
        if prediction == 0:
            return False, [], [], 0, 0
        
        # --- Candidate Generation ---
        # A full exact-hardware permutation search is O(N!), we map greedy-like candidates as proposals.
        valid_candidates = []
        for candidate_idx in range(5):  # Sample 5 different routing strategies locally 
            temp_graph = graph.copy()
            placements, paths_used, total_delay = [], [], 0
            prev_node = None
            placed_chain = True
            
            for vnf in chain:
                req_cpu = VNF_REQUIREMENTS[vnf]['cpu']
                req_ram = VNF_REQUIREMENTS[vnf]['ram']
                placed = False
                
                nodes = list(temp_graph.nodes())
                if candidate_idx == 0:
                    # Candidate 0: The Smart Candidate - Prioritize co-location
                    if prev_node is not None and prev_node in nodes:
                        nodes.remove(prev_node)
                        nodes.insert(0, prev_node)
                else:
                    # Candidates 1-4: The Explorers - Shuffle node traversal
                    random.shuffle(nodes)
                
                for node in nodes:
                    if temp_graph.nodes[node]['cpu_capacity'] >= req_cpu and temp_graph.nodes[node]['ram_capacity'] >= req_ram:
                        path_edges, path_delay, can_route = [], 0, True
                        
                        if prev_node is not None and prev_node != node:
                            try:
                                path_nodes = nx.shortest_path(temp_graph, source=prev_node, target=node)
                                for i in range(len(path_nodes) - 1):
                                    u, v = path_nodes[i], path_nodes[i+1]
                                    if temp_graph[u][v]['bandwidth'] < bw_demand:
                                        can_route = False
                                        break
                                if can_route:
                                    for i in range(len(path_nodes) - 1):
                                        u, v = path_nodes[i], path_nodes[i+1]
                                        path_edges.append((u, v))
                                        path_delay += temp_graph[u][v]['delay']
                            except nx.NetworkXNoPath:
                                can_route = False

                        if can_route:
                            # Tentative execution on candidate
                            temp_graph.nodes[node]['cpu_capacity'] -= req_cpu
                            temp_graph.nodes[node]['ram_capacity'] -= req_ram
                            for u, v in path_edges:
                                temp_graph[u][v]['bandwidth'] -= bw_demand
                                
                            placements.append((node, vnf, req_cpu, req_ram))
                            if path_edges: paths_used.append(path_edges)
                            total_delay += path_delay
                            prev_node = node
                            placed = True
                            break
                            
                if not placed:
                    placed_chain = False
                    break
            
            if placed_chain:
                unique_n = len(set([p[0] for p in placements]))
                action_max_path_distance = max([len(p) for p in paths_used]) if paths_used else 0
                valid_candidates.append({
                    'action_num_unique_nodes': unique_n,
                    'action_max_path_distance': action_max_path_distance,
                    'placements': placements,
                    'paths_used': paths_used,
                    'total_delay': total_delay
                })

        # --- ML Selection (Two-Stage Architecture) ---
        if not valid_candidates:
            return False, [], [], 0, 0

        # Stage 2: The Optimizer (Regressor)
        best_candidate = None
        best_pred_latency = float('inf')
        
        for c in valid_candidates:
            features = [state_array + [c['action_max_path_distance'], c['action_num_unique_nodes']]]
            pred_latency = self.regressor.predict(features)[0]
            
            # Agent Policy: Pick the candidate with the lowest expected Latency
            if pred_latency < best_pred_latency:
                best_pred_latency = pred_latency
                best_candidate = c
                
        # --- Main Execution ---
        for node, vnf, req_cpu, req_ram in best_candidate['placements']:
            graph.nodes[node]['cpu_capacity'] -= req_cpu
            graph.nodes[node]['ram_capacity'] -= req_ram
        for edges in best_candidate['paths_used']:
            for u, v in edges:
                graph[u][v]['bandwidth'] -= bw_demand

        return True, best_candidate['placements'], best_candidate['paths_used'], best_candidate['total_delay'], bw_demand


# ---------------------------------------------------------------------------
# Standalone training function
# ---------------------------------------------------------------------------

def train_models(data_path='telemetry_data.csv',
                 models_dir='models',
                 plots_dir='results/training_plots'):
    """Train the XGBoost classifier and regressor from telemetry data.

    Saves to:
      <models_dir>/kdn_classifier.json
      <models_dir>/kdn_regressor.json
      <models_dir>/label_encoder.pkl
      <plots_dir>/feature_distributions.png
      <plots_dir>/classifier_feature_importance.png
      <plots_dir>/classifier_confusion_matrix.png
      <plots_dir>/regressor_feature_importance.png
      <plots_dir>/regressor_actual_vs_predicted.png

    Returns:
      (classifier, regressor, encoder)
    """
    import os
    import pickle as _pickle
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder
    from sklearn.metrics import (accuracy_score, f1_score,
                                 mean_squared_error,
                                 confusion_matrix, ConfusionMatrixDisplay)

    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)

    # --- 1. Load data ---
    print(f"Loading data from '{data_path}' ...")
    df = pd.read_csv(data_path)
    print(f"  {len(df)} rows loaded.")

    # --- 2. Encode categorical feature ---
    encoder = LabelEncoder()
    df['sfc_type_encoded'] = encoder.fit_transform(df['sfc_type'])
    encoder_path = os.path.join(models_dir, 'label_encoder.pkl')
    with open(encoder_path, 'wb') as f:
        _pickle.dump(encoder, f)
    print(f"  Encoder saved -> {encoder_path}")

    # --- 3. Define features ---
    state_features = [
        'sfc_type_encoded', 'network_active_nodes', 'network_free_cpu',
        'network_free_bw', 'net_max_node_utilization', 'net_bottleneck_bw'
    ]
    action_features = ['action_max_path_distance', 'action_num_unique_nodes']

    X_cls = df[state_features]
    y_cls = df['outcome_accepted']

    df_accepted = df[df['outcome_accepted'] == 1].copy()
    X_reg = df_accepted[state_features + action_features]
    y_reg = df_accepted['outcome_latency']

    print(f"  Classifier samples : {len(X_cls)}")
    print(f"  Regressor samples  : {len(X_reg)}  (accepted only)")

    # --- 4. Feature distribution plot ---
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    axes[0].hist(df['network_free_cpu'], bins=30, alpha=0.7, label='network_free_cpu')
    axes[0].hist(df['network_free_bw'], bins=30, alpha=0.7, label='network_free_bw')
    axes[0].set_title('Distribution of Free CPU and Bandwidth')
    axes[0].set_xlabel('Value')
    axes[0].set_ylabel('Frequency')
    axes[0].legend()
    axes[1].hist(df['net_max_node_utilization'], bins=30, alpha=0.7, label='net_max_node_utilization')
    axes[1].hist(df['net_bottleneck_bw'], bins=30, alpha=0.7, label='net_bottleneck_bw')
    axes[1].set_title('Distribution of Max Node Utilization and Bottleneck BW')
    axes[1].set_xlabel('Value')
    axes[1].set_ylabel('Frequency')
    axes[1].legend()
    plt.tight_layout()
    p = os.path.join(plots_dir, 'feature_distributions.png')
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved -> {p}")

    # --- 5. Train classifier ---
    print("\nTraining Model A: Admission Control (XGBClassifier) ...")
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_cls, y_cls, test_size=0.2, random_state=42)
    classifier = xgb.XGBClassifier(
        objective='binary:logistic', n_estimators=150, max_depth=5, learning_rate=0.1)
    classifier.fit(X_train_c, y_train_c)
    preds_c = classifier.predict(X_test_c)
    print(f"  Accuracy : {accuracy_score(y_test_c, preds_c):.4f}")
    print(f"  F1-Score : {f1_score(y_test_c, preds_c):.4f}")

    # --- 6. Classifier feature importance ---
    fig, ax = plt.subplots(figsize=(8, 5))
    xgb.plot_importance(classifier, max_num_features=10, ax=ax)
    ax.set_title('Feature Importance - Admission Control (Classifier)')
    plt.tight_layout()
    p = os.path.join(plots_dir, 'classifier_feature_importance.png')
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved -> {p}")

    # --- 7. Confusion matrix ---
    cm = confusion_matrix(y_test_c, preds_c)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=classifier.classes_)
    fig, ax = plt.subplots(figsize=(6, 5))
    disp.plot(cmap=plt.cm.Blues, ax=ax)
    ax.set_title('Confusion Matrix - Admission Control (Classifier)')
    plt.tight_layout()
    p = os.path.join(plots_dir, 'classifier_confusion_matrix.png')
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved -> {p}")

    # --- 8. Train regressor ---
    print("\nTraining Model B: Latency Optimizer (XGBRegressor) ...")
    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
        X_reg, y_reg, test_size=0.2, random_state=42)
    regressor = xgb.XGBRegressor(
        objective='reg:squarederror', n_estimators=150, max_depth=5, learning_rate=0.1)
    regressor.fit(X_train_r, y_train_r)
    preds_r = regressor.predict(X_test_r)
    rmse = np.sqrt(mean_squared_error(y_test_r, preds_r))
    print(f"  RMSE : {rmse:.2f}")

    # --- 9. Regressor feature importance ---
    fig, ax = plt.subplots(figsize=(8, 5))
    xgb.plot_importance(regressor, max_num_features=10, ax=ax)
    ax.set_title('Feature Importance - Latency Optimizer (Regressor)')
    plt.tight_layout()
    p = os.path.join(plots_dir, 'regressor_feature_importance.png')
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved -> {p}")

    # --- 10. Actual vs predicted ---
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(y_test_r, preds_r, alpha=0.7)
    ax.plot([y_test_r.min(), y_test_r.max()],
            [y_test_r.min(), y_test_r.max()], 'r--')
    ax.set_title('Actual vs Predicted Latency - Latency Optimizer (Regressor)')
    ax.set_xlabel('Actual Latency (ms)')
    ax.set_ylabel('Predicted Latency (ms)')
    plt.tight_layout()
    p = os.path.join(plots_dir, 'regressor_actual_vs_predicted.png')
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved -> {p}")

    # --- 11. Save models ---
    cls_path = os.path.join(models_dir, 'kdn_classifier.json')
    reg_path = os.path.join(models_dir, 'kdn_regressor.json')
    classifier.save_model(cls_path)
    regressor.save_model(reg_path)
    print(f"\n  Saved Gatekeeper -> {cls_path}")
    print(f"  Saved Optimizer  -> {reg_path}")
    print("\nTraining complete.")
    return classifier, regressor, encoder


if __name__ == '__main__':
    train_models()