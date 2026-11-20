"""Experiment runs: simulation grid, telemetry generation, model training and calibration (protocol sections 3-5)."""
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from src.environment import SPLIT_CODES, Simulation, World, load_env_config, summarize
from src.features import VNF_RAW, net_rho, vnf_matrix, vnf_rows
from src.policies import build_policy

XGB_PARAMS = dict(n_estimators=150, max_depth=5, learning_rate=0.1)
_WORLDS = {}


def world_for(env_path):
    if env_path not in _WORLDS:
        _WORLDS[env_path] = World(load_env_config(env_path))
    return _WORLDS[env_path]


def policy_rng(seed, lam, split):
    return np.random.default_rng([seed, int(round(lam * 10000)), SPLIT_CODES[split], 99])


def run_single(env_path, policy, seed, lam, split, horizon, warmup, models_dir=None, alpha_star=None,
               observer=None):
    world = world_for(env_path)
    graph = world.build_graph()
    sched, start = world.schedule(split, seed, lam, horizon)
    algo = build_policy(policy, world, policy_rng(seed, lam, split), models_dir, alpha_star)
    sim = Simulation(world, graph, algo, sched, observer=observer).run(until=horizon)
    return {'algorithm': policy, 'seed': seed, 'lambda': lam, 'split': split, 'tm_start': start,
            **summarize(sim, warmup)}


def _job(args):
    return run_single(*args)


def _map(fn, tasks, jobs):
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as ex:
            return list(ex.map(fn, tasks, chunksize=1))
    return [fn(t) for t in tasks]


def run_grid(env_path, policies, seeds, lambdas, split, horizon, warmup, models_dir=None, alpha_star=None, jobs=1):
    """Every (lambda, seed, policy) cell; every policy sees identical traffic for a given (seed, lambda)."""
    tasks = [(env_path, p, s, lam, split, horizon, warmup, models_dir, alpha_star)
             for lam in lambdas for s in seeds for p in policies]
    return pd.DataFrame(_map(_job, tasks, jobs))


# --- training telemetry (protocol section 4) ------------------------------------------------------
TELEMETRY_COLUMNS = ['seed', 'lambda', 'time', 'req_id', 'sfc_type', 'generator', 'vnf', 'node', *VNF_RAW,
                     'rho_after', 'delay']


class TelemetryLog:
    """For every accepted request, one row per VNF: pre-placement features, measured host utilisation
    after placement and the measured VNF processing delay."""

    def __init__(self, world, seed, lam):
        self.world, self.seed, self.lam, self.rows = world, seed, lam, []

    def __call__(self, now, req, graph, res):
        if not res.success:
            return
        added = self.world.added_loads(res, req)
        rows = vnf_rows(graph, req, res, net_rho(graph))
        for (node, vnf, _, _), r, d in zip(res.placements, rows, res.info['vnf_delays']):
            after = (graph.nodes[node]['load'] + added[node]) / graph.nodes[node]['cpu_max']
            self.rows.append([self.seed, self.lam, now, req.req_id, req.sfc_type, res.info.get('generator', ''),
                              vnf, node, *[r[k] for k in VNF_RAW], after, d])


def _telemetry_job(args):
    env_path, seed, lam, horizon = args
    log = TelemetryLog(world_for(env_path), seed, lam)
    run_single(env_path, 'behaviour', seed, lam, 'train', horizon, 0.0, observer=log)
    return log.rows


def generate_telemetry(env_path, seeds, lambdas, horizon, jobs=1):
    tasks = [(env_path, s, lam, horizon) for lam in lambdas for s in seeds]
    parts = _map(_telemetry_job, tasks, jobs)
    return pd.DataFrame([r for p in parts for r in p], columns=TELEMETRY_COLUMNS)


# --- model training and analytical calibration ----------------------------------------------------
def fit_calibration(df, service_ms, rho_max, cpu_max):
    """model-nom / model-cal parameters from training telemetry (protocol section 3).

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


def train_models(df, models_dir, val_seeds, world):
    """KDN regressor + analytical calibration, fitted on non-validation seeds; validation metrics for all three."""
    import xgboost as xgb
    from sklearn.metrics import mean_absolute_error, r2_score
    os.makedirs(models_dir, exist_ok=True)
    val = df['seed'].isin(val_seeds)
    tr, va = df[~val], df[val]
    reg = xgb.XGBRegressor(objective='reg:squarederror', **XGB_PARAMS).fit(vnf_matrix(tr), tr['delay'])
    service, rho_max, cpu_max = world.cfg['service_ms'], world.cfg['rho_max'], world.cfg['node_cpu']
    cal = fit_calibration(tr, service, rho_max, cpu_max)
    key = ['seed', 'lambda', 'req_id']
    preds = {'kdn': reg.predict(vnf_matrix(va)),
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
    reg.save_model(os.path.join(models_dir, 'kdn_regressor.json'))
    with open(os.path.join(models_dir, 'calibration.json'), 'w') as f:
        json.dump(cal, f, indent=2)
    return metrics
