"""Train the two-stage KDN models (gatekeeper classifier + latency regressor) from telemetry."""
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, confusion_matrix, f1_score,
                             mean_squared_error, precision_score, recall_score)
from sklearn.model_selection import train_test_split

from src.features import ACTION_FEATURES, STATE_FEATURES
from src.sfc import SFC_CODES

XGB_PARAMS = dict(n_estimators=150, max_depth=5, learning_rate=0.1)


def load_telemetry(path):
    df = pd.read_csv(path)
    df['sfc_type_encoded'] = df['sfc_type'].map(SFC_CODES)
    return df


def train_models(data_path, models_dir='models', plots_dir=None, test_size=0.2, split_seed=42):
    """Train and save ``kdn_classifier.json`` / ``kdn_regressor.json``; returns a metrics dict.

    v1 protocol: random 80/20 split (``split_seed``), same hyper-parameters for both models.
    """
    os.makedirs(models_dir, exist_ok=True)
    df = load_telemetry(data_path)
    X_cls, y_cls = df[STATE_FEATURES], df['outcome_accepted']
    acc_df = df[df['outcome_accepted'] == 1]
    X_reg, y_reg = acc_df[STATE_FEATURES + ACTION_FEATURES], acc_df['outcome_latency']

    Xtr, Xte, ytr, yte = train_test_split(X_cls, y_cls, test_size=test_size, random_state=split_seed)
    clf = xgb.XGBClassifier(objective='binary:logistic', **XGB_PARAMS).fit(Xtr, ytr)
    pc = clf.predict(Xte)

    Xtr_r, Xte_r, ytr_r, yte_r = train_test_split(X_reg, y_reg, test_size=test_size, random_state=split_seed)
    reg = xgb.XGBRegressor(objective='reg:squarederror', **XGB_PARAMS).fit(Xtr_r, ytr_r)
    pr = reg.predict(Xte_r)

    metrics = {
        'rows': int(len(df)), 'regressor_rows': int(len(acc_df)),
        'clf_accuracy': float(accuracy_score(yte, pc)), 'clf_f1': float(f1_score(yte, pc)),
        'clf_precision': float(precision_score(yte, pc)), 'clf_recall': float(recall_score(yte, pc)),
        'clf_confusion': confusion_matrix(yte, pc).tolist(),
        'reg_rmse': float(np.sqrt(mean_squared_error(yte_r, pr))),
    }
    clf.save_model(os.path.join(models_dir, 'kdn_classifier.json'))
    reg.save_model(os.path.join(models_dir, 'kdn_regressor.json'))
    with open(os.path.join(models_dir, 'training_metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)

    if plots_dir:
        _plots(plots_dir, clf, reg, yte, pc, yte_r, pr)
    return metrics


def _plots(plots_dir, clf, reg, yte, pc, yte_r, pr):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    os.makedirs(plots_dir, exist_ok=True)
    for model, name in ((clf, 'classifier'), (reg, 'regressor')):
        fig, ax = plt.subplots(figsize=(8, 5))
        xgb.plot_importance(model, importance_type='gain', ax=ax, show_values=False)
        ax.set_title(f'Feature importance (gain) - {name}')
        fig.tight_layout(); fig.savefig(os.path.join(plots_dir, f'{name}_importance_gain.png'), dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay(confusion_matrix(yte, pc)).plot(cmap=plt.cm.Blues, ax=ax)
    fig.tight_layout(); fig.savefig(os.path.join(plots_dir, 'classifier_confusion_matrix.png'), dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(yte_r, pr, alpha=0.3, s=6)
    lo, hi = float(min(yte_r.min(), pr.min())), float(max(yte_r.max(), pr.max()))
    ax.plot([lo, hi], [lo, hi], 'r--'); ax.set_xlabel('Actual latency (ms)'); ax.set_ylabel('Predicted latency (ms)')
    fig.tight_layout(); fig.savefig(os.path.join(plots_dir, 'regressor_actual_vs_predicted.png'), dpi=150); plt.close(fig)
