"""v2 runs: data generation, model training, alpha tuning and evaluation (protocol sections 3-6)."""
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from src.engine import summarize
from src.v2.environment import SPLIT_CODES, V2Simulation, V2World, load_env_config
from src.v2.features import CANDIDATE_FEATURES, STATE_FEATURES, candidate_features, state_features
from src.v2.policies import build_policy

_WORLDS = {}


def world_for(env_path):
    if env_path not in _WORLDS:
        _WORLDS[env_path] = V2World(load_env_config(env_path))
    return _WORLDS[env_path]


def policy_rng(seed, lam, split):
    return np.random.default_rng([seed, int(round(lam * 10000)), SPLIT_CODES[split], 99])


def run_single(env_path, policy, seed, lam, split, horizon, warmup, models_dir=None, alpha_star=None,
               observer=None):
    world = world_for(env_path)
    graph = world.build_graph()
    sched, start = world.schedule(split, seed, lam, horizon)
    algo = build_policy(policy, world, policy_rng(seed, lam, split), models_dir, alpha_star)
    sim = V2Simulation(world, graph, algo, sched, observer=observer).run(until=horizon)
    row = {'algorithm': policy, 'seed': seed, 'lambda': lam, 'split': split, 'tm_start': start,
           **summarize(sim, warmup)}
    return row


def _job(args):
    return run_single(*args)


def run_grid(env_path, policies, seeds, lambdas, split, horizon, warmup, models_dir=None, alpha_star=None, jobs=1):
    tasks = [(env_path, p, s, lam, split, horizon, warmup, models_dir, alpha_star)
             for lam in lambdas for s in seeds for p in policies]
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as ex:
            rows = list(ex.map(_job, tasks, chunksize=1))
    else:
        rows = [_job(t) for t in tasks]
    return pd.DataFrame(rows)


# --- training data -------------------------------------------------------------------------
class TelemetryLog:
    def __init__(self, seed, lam):
        self.seed, self.lam, self.rows = seed, lam, []

    def __call__(self, now, req, graph, res):
        st = state_features(graph, req)
        cf = candidate_features(graph, req, res) if res.success else [np.nan] * len(CANDIDATE_FEATURES)
        self.rows.append([self.seed, self.lam, now, req.sfc_type, int(res.success),
                          res.info.get('prop_delay', np.nan), res.info.get('proc_delay', np.nan),
                          res.info.get('generator', ''), *st, *cf])


TELEMETRY_COLUMNS = (['seed', 'lambda', 'time', 'sfc_type', 'accepted', 'prop_delay', 'proc_delay', 'generator'] +
                     [f's_{c}' for c in STATE_FEATURES] + [f'c_{c}' for c in CANDIDATE_FEATURES])


def _datagen_job(args):
    env_path, seed, lam, horizon = args
    log = TelemetryLog(seed, lam)
    run_single(env_path, 'behaviour', seed, lam, 'train', horizon, 0.0, observer=log)
    return log.rows


def generate_training_data(env_path, seeds, lambdas, horizon, jobs=1):
    tasks = [(env_path, s, lam, horizon) for lam in lambdas for s in seeds]
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as ex:
            parts = list(ex.map(_datagen_job, tasks, chunksize=1))
    else:
        parts = [_datagen_job(t) for t in tasks]
    return pd.DataFrame([r for p in parts for r in p], columns=TELEMETRY_COLUMNS)


XGB_PARAMS = dict(n_estimators=150, max_depth=5, learning_rate=0.1)


def train_models(df, models_dir, val_seeds):
    """Regressor: processing delay of the chosen candidate. Classifier (ablation gate): acceptance."""
    import xgboost as xgb
    from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, r2_score, roc_auc_score
    os.makedirs(models_dir, exist_ok=True)
    val = df['seed'].isin(val_seeds)
    acc = df['accepted'] == 1
    Xc = [f'c_{c}' for c in CANDIDATE_FEATURES]
    Xs = [f's_{c}' for c in STATE_FEATURES]
    reg = xgb.XGBRegressor(objective='reg:squarederror', **XGB_PARAMS).fit(df.loc[acc & ~val, Xc],
                                                                           df.loc[acc & ~val, 'proc_delay'])
    yv, pv = df.loc[acc & val, 'proc_delay'], reg.predict(df.loc[acc & val, Xc])
    clf = xgb.XGBClassifier(objective='binary:logistic', **XGB_PARAMS).fit(df.loc[~val, Xs], df.loc[~val, 'accepted'])
    cv, cp = df.loc[val, 'accepted'], clf.predict_proba(df.loc[val, Xs])[:, 1]
    metrics = {
        'train_rows': int((~val).sum()), 'val_rows': int(val.sum()),
        'reg_val_rmse': float(np.sqrt(mean_squared_error(yv, pv))), 'reg_val_mae': float(mean_absolute_error(yv, pv)),
        'reg_val_r2': float(r2_score(yv, pv)), 'reg_val_target_mean': float(yv.mean()),
        'clf_val_accuracy': float(accuracy_score(cv, cp > 0.5)), 'clf_val_f1': float(f1_score(cv, cp > 0.5)),
        'clf_val_auc': float(roc_auc_score(cv, cp)),
    }
    reg.save_model(os.path.join(models_dir, 'kdn2_regressor.json'))
    clf.save_model(os.path.join(models_dir, 'kdn2_classifier.json'))
    with open(os.path.join(models_dir, 'training_metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
    return metrics
