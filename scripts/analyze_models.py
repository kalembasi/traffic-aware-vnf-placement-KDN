"""Honest evaluation of the KDN models themselves (not the placement outcome).

1. Gatekeeper classifier: random split (v1 protocol) vs chronological split, ROC-AUC, trivial baselines.
2. Latency regressor: RMSE/MAE/R2 vs baselines, random vs chronological split.
3. SHAP-style contributions (XGBoost pred_contribs) of the deployed v1 models.
4. Decision quality inside the simulator: how often the regressor picks the candidate with the
   lowest *true* latency (which is known at decision time), and the resulting regret.

Usage: python -m scripts.analyze_models --data data/telemetry_v1.csv --models-dir models/v1 --out results/v1_models
"""
import argparse
import copy
import json
import os
import random

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy import stats
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score,
                             r2_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src.algorithms.kdn import KDNPlacement
from src.engine import Simulation, generate_schedule
from src.features import ACTION_FEATURES, STATE_FEATURES
from src.topology import create_topology
from src.training import XGB_PARAMS, load_telemetry


def chrono_split(df, test_frac=0.2):
    """Last ``test_frac`` of every traffic profile goes to test (no near-duplicate neighbours across sets)."""
    tr, te = [], []
    for _, g in df.groupby('profile', sort=False):
        cut = int(len(g) * (1 - test_frac))
        tr.append(g.iloc[:cut]); te.append(g.iloc[cut:])
    return pd.concat(tr), pd.concat(te)


def random_split(df, seed=42):
    return train_test_split(df, test_size=0.2, random_state=seed)


def clf_models():
    return {
        'majority': DummyClassifier(strategy='most_frequent'),
        'tree-depth2(sfc,free_cpu)': ('cols', ['sfc_type_encoded', 'network_free_cpu'], DecisionTreeClassifier(max_depth=2)),
        'logistic': make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        'xgboost (v1)': xgb.XGBClassifier(objective='binary:logistic', **XGB_PARAMS),
    }


def reg_models():
    return {
        'mean': DummyRegressor(),
        'linear(action only)': ('cols', ACTION_FEATURES, LinearRegression()),
        'linear(all)': LinearRegression(),
        'xgboost (v1)': xgb.XGBRegressor(objective='reg:squarederror', **XGB_PARAMS),
    }


def _fit_predict(spec, Xtr, ytr, Xte, proba=False):
    cols = None
    if isinstance(spec, tuple):
        _, cols, spec = spec
        Xtr, Xte = Xtr[cols], Xte[cols]
    spec.fit(Xtr, ytr)
    if proba:
        return spec.predict(Xte), spec.predict_proba(Xte)[:, 1]
    return spec.predict(Xte)


def eval_classifier(df):
    rows = []
    for split_name, (tr, te) in {'random (v1)': random_split(df), 'chronological': chrono_split(df)}.items():
        for name, spec in clf_models().items():
            yhat, p = _fit_predict(spec, tr[STATE_FEATURES], tr['outcome_accepted'], te[STATE_FEATURES], proba=True)
            y = te['outcome_accepted']
            rows.append({'split': split_name, 'model': name, 'accuracy': accuracy_score(y, yhat),
                         'precision': precision_score(y, yhat, zero_division=0), 'recall': recall_score(y, yhat),
                         'f1': f1_score(y, yhat), 'roc_auc': roc_auc_score(y, p) if len(set(p)) > 1 else 0.5})
    return pd.DataFrame(rows)


def eval_regressor(df):
    acc = df[df['outcome_accepted'] == 1]
    rows = []
    for split_name, (tr, te) in {'random (v1)': random_split(acc), 'chronological': chrono_split(acc)}.items():
        X = STATE_FEATURES + ACTION_FEATURES
        for name, spec in reg_models().items():
            yhat = _fit_predict(spec, tr[X], tr['outcome_latency'], te[X])
            y = te['outcome_latency']
            rows.append({'split': split_name, 'model': name, 'rmse': float(np.sqrt(mean_squared_error(y, yhat))),
                         'mae': mean_absolute_error(y, yhat), 'r2': r2_score(y, yhat)})
    return pd.DataFrame(rows)


def contributions(models_dir, df):
    """Mean |SHAP| per feature for the deployed v1 models (XGBoost TreeSHAP via pred_contribs)."""
    out = []
    clf = xgb.XGBClassifier(); clf.load_model(os.path.join(models_dir, 'kdn_classifier.json'))
    reg = xgb.XGBRegressor(); reg.load_model(os.path.join(models_dir, 'kdn_regressor.json'))
    acc = df[df['outcome_accepted'] == 1]
    for name, model, X in (('classifier', clf, df[STATE_FEATURES]),
                           ('regressor', reg, acc[STATE_FEATURES + ACTION_FEATURES])):
        c = model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)[:, :-1]
        gain = model.get_booster().get_score(importance_type='gain')
        tot = sum(gain.values())
        for i, f in enumerate(X.columns):
            out.append({'model': name, 'feature': f, 'mean_abs_shap': float(np.abs(c[:, i]).mean()),
                        'gain_share': gain.get(f, 0.0) / tot})
    return pd.DataFrame(out)


def decision_quality(config, models_dir, seeds, lam=0.2, end=10000, warmup=1200):
    """Run the v1 KDN policy and inspect every regressor decision against the true candidate latencies."""
    rows = []
    for seed in seeds:
        cfg = copy.deepcopy(config)
        cfg['simulation']['lambda_rate'] = lam
        random.seed(seed)
        g = create_topology(cfg)
        sched = generate_schedule(cfg['simulation'], end, rng=random)
        log = []

        def obs(now, req, graph, res):
            if res.success and now >= warmup and 'cand_preds' in res.info:
                log.append((res.delay, res.info['cand_delays'], res.info['cand_preds']))
        Simulation(g, KDNPlacement(models_dir), schedule=sched, observer=obs, monitor_interval=None).run(until=end)
        for chosen, d, p in log:
            d, p = np.array(d), np.array(p)
            distinct = len(set(d)) > 1
            rows.append({'seed': seed, 'n_cands': len(d), 'distinct': distinct,
                         'picked_oracle': chosen == d.min(), 'regret': chosen - d.min(),
                         'spearman': stats.spearmanr(p, d).statistic if distinct and len(set(p)) > 1 else np.nan,
                         'colocated_available': bool((d == 0).any())})
    return pd.DataFrame(rows)


def gate_quality(config, models_dir, seeds, lams=(0.1, 0.2, 0.4), end=10000, warmup=1200):
    """For every gatekeeper decision, check whether first-fit (Greedy, no RNG) could have placed the request.

    Greedy-feasibility is exactly the label the classifier was trained on.
    """
    from src.placement import build_chain
    rows = []
    for lam in lams:
        for seed in seeds:
            cfg = copy.deepcopy(config)
            cfg['simulation']['lambda_rate'] = lam
            random.seed(seed)
            g = create_topology(cfg)
            sched = generate_schedule(cfg['simulation'], end, rng=random)

            def obs(now, req, graph, res):
                if now < warmup:
                    return
                feasible = build_chain(graph, req.chain, req.bandwidth).success
                rows.append({'lambda': lam, 'seed': seed, 'sfc_type': req.sfc_type, 'gate_reject': res.reason == 'gate',
                             'greedy_feasible': feasible, 'accepted': res.success})
            Simulation(g, KDNPlacement(models_dir), schedule=sched, observer=obs, monitor_interval=None).run(until=end)
    df = pd.DataFrame(rows)
    out = []
    for (lam, t), d in df.groupby(['lambda', 'sfc_type']):
        gr = d[d.gate_reject]
        out.append({'lambda': lam, 'sfc_type': t, 'requests': len(d), 'gate_reject_rate': d.gate_reject.mean(),
                    'feasible_rate': d.greedy_feasible.mean(),
                    'false_reject_share': gr.greedy_feasible.mean() if len(gr) else np.nan,
                    'missed_feasible_rate': (d.gate_reject & d.greedy_feasible).mean(),
                    'acceptance': d.accepted.mean()})
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data', required=True)
    ap.add_argument('--models-dir', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--config', default='config/config.json')
    ap.add_argument('--seeds', type=int, default=10)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with open(a.config) as f:
        config = json.load(f)
    df = load_telemetry(a.data)

    cls = eval_classifier(df); cls.to_csv(os.path.join(a.out, 'classifier_eval.csv'), index=False)
    reg = eval_regressor(df); reg.to_csv(os.path.join(a.out, 'regressor_eval.csv'), index=False)
    con = contributions(a.models_dir, df); con.to_csv(os.path.join(a.out, 'feature_contributions.csv'), index=False)
    dq = decision_quality(config, a.models_dir, list(range(1, a.seeds + 1)))
    dq.to_csv(os.path.join(a.out, 'decision_quality.csv.gz'), index=False)

    gq = gate_quality(config, a.models_dir, list(range(1, a.seeds + 1)))
    gq.to_csv(os.path.join(a.out, 'gate_quality.csv'), index=False)

    dd = dq[dq.distinct]
    dq_summary = {
        'decisions': int(len(dq)),
        'decisions_with_distinct_candidate_latencies': int(len(dd)),
        'share_distinct': float(dq.distinct.mean()),
        'picked_true_min_all': float(dq.picked_oracle.mean()),
        'picked_true_min_when_distinct': float(dd.picked_oracle.mean()),
        'mean_regret_ms_all': float(dq.regret.mean()),
        'mean_regret_ms_when_distinct': float(dd.regret.mean()),
        'median_spearman_pred_vs_true_when_distinct': float(dd.spearman.median()),
    }
    with open(os.path.join(a.out, 'decision_quality_summary.json'), 'w') as f:
        json.dump(dq_summary, f, indent=2)

    fmt = lambda d: d.to_markdown(index=False, floatfmt='.3f')
    md = ["# v1 KDN models: honest model-level evaluation", "",
          "## Gatekeeper classifier", "", fmt(cls), "",
          "## Latency regressor (accepted requests only)", "", fmt(reg), "",
          "## Feature contributions of deployed models (mean |SHAP|, gain share)", "",
          fmt(con.sort_values(['model', 'mean_abs_shap'], ascending=[True, False])), "",
          f"## Decision quality inside the simulator (lambda=0.2, {a.seeds} seeds, after warm-up)", "",
          "```json", json.dumps(dq_summary, indent=2), "```", "",
          f"## Gatekeeper decisions vs Greedy-feasibility ({a.seeds} seeds, after warm-up)", "",
          "false_reject_share = share of gate rejections that first-fit could have placed;",
          "missed_feasible_rate = share of all requests rejected by the gate although feasible.", "",
          fmt(gq), ""]
    with open(os.path.join(a.out, 'models_report.md'), 'w') as f:
        f.write('\n'.join(md))
    print('\n'.join(md))


if __name__ == '__main__':
    main()
