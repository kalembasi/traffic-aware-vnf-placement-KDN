import os

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(not os.path.exists('data/external/sndlib/abilene.txt'),
                                reason='run scripts/fetch_data.sh first')
S05 = 'experiments/v3/env_s05.json'


def test_speed_factors_follow_protocol():
    from src.v2.experiment import world_for
    k0 = world_for('experiments/v3/env_s0.json').speed
    k05, k1 = world_for(S05).speed, world_for('experiments/v3/env_s1.json').speed
    assert all(v == 1.0 for v in k0.values())
    for k in (k05, k1):
        assert abs(np.mean(np.log(list(k.values())))) < 1e-12           # geometric mean 1
    nodes = sorted(k05)
    assert np.argsort([k05[n] for n in nodes]).tolist() == np.argsort([k1[n] for n in nodes]).tolist()
    assert max(k1.values()) == pytest.approx(5.65, abs=0.01) and min(k05.values()) == pytest.approx(0.42, abs=0.01)
    perm2 = world_for('experiments/v3/env_s05_perm2.json').speed
    assert sorted(perm2.values()) == pytest.approx(sorted(k05.values())) and perm2 != k05
    # v2 environments have no heterogeneity
    assert set(world_for('experiments/v2/env_main.json').speed.values()) == {1.0}


def test_v3_has_no_wake_up_penalty():
    from src.v2.experiment import policy_rng, world_for
    from src.v2.policies import build_policy
    w3, w2 = world_for(S05), world_for('experiments/v2/env_main.json')
    assert build_policy('smart', w3, policy_rng(1, 0.1, 'test')).wake_up_penalty == 0.0
    assert build_policy('smart', w2, policy_rng(1, 0.1, 'test')).wake_up_penalty == 1000.0
    o = build_policy('oracle', w3, policy_rng(1, 0.1, 'test'))
    assert all(g.wake_up_penalty == 0.0 for g in o.generators if hasattr(g, 'wake_up_penalty'))


@pytest.fixture(scope='module')
def trained(tmp_path_factory):
    from src.v2.experiment import generate_vnf_telemetry, train_v3, world_for
    df = generate_vnf_telemetry(S05, [1, 2, 3], [0.2], 2000)
    d = str(tmp_path_factory.mktemp('m'))
    return df, d, train_v3(df, d, [3], world_for(S05))


def test_vnf_telemetry_matches_true_delay(trained):
    df, _, _ = trained
    from src.v2.experiment import world_for
    w = world_for(S05)
    s = df.vnf.map(w.cfg['service_ms']) * df.node.map(w.speed)
    assert np.allclose(df.delay, s / (1 - np.minimum(df.rho_after, 0.95)))
    assert (df.rho_after >= df.rho_before).all()


def test_calibration_recovers_hidden_parameters(trained):
    _, _, m = trained
    for n, (hat, true) in m['kappa_hat_vs_true'].items():
        assert hat == pytest.approx(true, rel=1e-9)       # deterministic delay given the measured rho_after
    assert 0.5 < m['u0_hat'] < 0.7                        # u0 = 0.6 times the mean relative load r
    assert m['model-cal']['vnf_r2'] > m['model-nom']['vnf_r2']


@pytest.mark.parametrize('policy', ['model-nom', 'model-cal', 'kdn3', 'cands-prop'])
def test_v3_selectors_conserve_resources(trained, policy):
    from src.v2.environment import V2Simulation
    from src.v2.experiment import policy_rng, world_for
    from src.v2.policies import build_policy
    _, d, _ = trained
    w = world_for(S05)
    g = w.build_graph()
    sched, _ = w.schedule('train', 5, 0.3, 1500)
    sim = V2Simulation(w, g, build_policy(policy, w, policy_rng(5, 0.3, 'train'), models_dir=d), sched)
    sim.run(until=1500)
    assert sum(r.accepted for r in sim.records) > 0
    sim.env.run(until=1500 + 601)
    for n in g.nodes:
        assert g.nodes[n]['cpu_capacity'] == g.nodes[n]['cpu_max'] and abs(g.nodes[n]['load']) < 1e-9


def test_model_selector_prediction_is_exact_with_true_parameters(trained):
    """With kappa_hat = true kappa and u0_hat * r matching, model-cal reproduces the true processing delay."""
    from src.v2.experiment import policy_rng, world_for
    from src.v2.policies import build_policy
    _, d, _ = trained
    w = world_for(S05)
    g = w.build_graph()
    sel = build_policy('model-cal', w, policy_rng(1, 0.2, 'train'), models_dir=d)
    sched, _ = w.schedule('train', 1, 0.2, 300)
    req = sched[0].request
    req.hidden['r'] = [sel.u0_hat / w.cfg['u0']] * len(req.chain)
    c = sel.candidates(g, req)[0]
    assert sel.predict(g, req, c) == pytest.approx(w.processing_delay(g, c, req), rel=1e-9)
