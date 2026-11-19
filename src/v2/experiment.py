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


# --- v3: per-VNF telemetry, kdn3 training, analytical calibration (v3 protocol section 4) ---------
from src.v2.features import VNF_ORDER, VNF_RAW, _net, vnf_matrix, vnf_rows  # noqa: E402

VNF_TELEMETRY_COLUMNS = ['seed', 'lambda', 'time', 'req_id', 'sfc_type', 'generator', 'vnf', 'node', *VNF_RAW,
                         'rho_after', 'delay']


class VNFTelemetryLog:
    """Logs, for every accepted request, one row per VNF: pre-placement features, measured host
    utilisation after placement and the measured VNF processing delay."""

    def __init__(self, world, seed, lam):
        self.world, self.seed, self.lam, self.rows = world, seed, lam, []

    def __call__(self, now, req, graph, res):
        if not res.success:
            return
        added = self.world.added_loads(res, req)
        rows = vnf_rows(graph, req, res, _net(graph)[0])
        for (node, vnf, _, _), r, d in zip(res.placements, rows, res.info['vnf_delays']):
            after = (graph.nodes[node]['load'] + added[node]) / graph.nodes[node]['cpu_max']
            self.rows.append([self.seed, self.lam, now, req.req_id, req.sfc_type, res.info.get('generator', ''),
                              vnf, node, *[r[k] for k in VNF_RAW], after, d])


def _vnf_datagen_job(args):
    env_path, seed, lam, horizon = args
    log = VNFTelemetryLog(world_for(env_path), seed, lam)
    run_single(env_path, 'behaviour', seed, lam, 'train', horizon, 0.0, observer=log)
    return log.rows


def generate_vnf_telemetry(env_path, seeds, lambdas, horizon, jobs=1):
    tasks = [(env_path, s, lam, horizon) for lam in lambdas for s in seeds]
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as ex:
            parts = list(ex.map(_vnf_datagen_job, tasks, chunksize=1))
    else:
        parts = [_vnf_datagen_job(t) for t in tasks]
    return pd.DataFrame([r for p in parts for r in p], columns=VNF_TELEMETRY_COLUMNS)


def fit_calibration(df, service_ms, rho_max, cpu_max):
    """model-nom / model-cal parameters from training telemetry (v3 protocol section 3).

    u0_hat  : observed load increase on a host / CPU the SFC reserved there (one scalar).
    kappa_hat[n] : median of observed delay / (s_v / (1 - min(rho_after, rho_max))) over VNFs on n.
    """
    per_host = df.drop_duplicates(['seed', 'lambda', 'req_id', 'node'])
    u0_hat = float(((per_host.rho_after - per_host.rho_before) * cpu_max).sum() / per_host.cpu_res_host.sum())
    nominal = df.vnf.map(service_ms) / (1.0 - np.minimum(df.rho_after, rho_max))
    kappa_hat = (df.delay / nominal).groupby(df.node).median()
    return {'u0_hat': u0_hat, 'kappa_hat': {k: float(v) for k, v in kappa_hat.items()}}


def model_prediction(df, cal, service_ms, rho_max, cpu_max, calibrated):
    """Per-VNF delay predicted by model-nom/model-cal from pre-placement information only."""
    rho_hat = df.rho_before + cal['u0_hat'] * df.cpu_res_host / cpu_max
    kappa = df.node.map(cal['kappa_hat']).fillna(1.0) if calibrated else 1.0
    return kappa * df.vnf.map(service_ms) / (1.0 - np.minimum(rho_hat, rho_max))


def train_v3(df, models_dir, val_seeds, world):
    """kdn3 regressor + analytical calibration, fitted on non-validation seeds; validation metrics for all three."""
    import xgboost as xgb
    from sklearn.metrics import mean_absolute_error, r2_score
    os.makedirs(models_dir, exist_ok=True)
    val = df['seed'].isin(val_seeds)
    tr, va = df[~val], df[val]
    reg = xgb.XGBRegressor(objective='reg:squarederror', **XGB_PARAMS).fit(vnf_matrix(tr), tr['delay'])
    service, rho_max, cpu_max = world.cfg['service_ms'], world.cfg['rho_max'], world.cfg['node_cpu']
    cal = fit_calibration(tr, service, rho_max, cpu_max)
    key = ['seed', 'lambda', 'req_id']
    preds = {'kdn3': reg.predict(vnf_matrix(va)),
             'model-nom': model_prediction(va, cal, service, rho_max, cpu_max, False).to_numpy(),
             'model-cal': model_prediction(va, cal, service, rho_max, cpu_max, True).to_numpy()}
    metrics = {'train_rows': int(len(tr)), 'val_rows': int(len(va)), 'val_target_mean': float(va.delay.mean()),
               'u0_hat': cal['u0_hat'], 'u0_true': world.cfg['u0'],
               'kappa_hat_vs_true': {n: [cal['kappa_hat'].get(n), world.speed[n]] for n in sorted(world.speed)}}
    for name, p in preds.items():
        req_true = va.groupby(key).delay.sum()
        req_pred = pd.Series(p, index=va.index).groupby([va[k] for k in key]).sum()
        metrics[name] = {'vnf_r2': float(r2_score(va.delay, p)), 'vnf_mae': float(mean_absolute_error(va.delay, p)),
                         'request_r2': float(r2_score(req_true, req_pred)),
                         'request_mae': float(mean_absolute_error(req_true, req_pred))}
    reg.save_model(os.path.join(models_dir, 'kdn3_regressor.json'))
    with open(os.path.join(models_dir, 'calibration.json'), 'w') as f:
        json.dump(cal, f, indent=2)
    with open(os.path.join(models_dir, 'training_metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
    return metrics
