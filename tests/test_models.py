import numpy as np
import pytest

from tests.conftest import S05, needs_data

pytestmark = needs_data


@pytest.fixture(scope='module')
def trained(tmp_path_factory):
    from src.experiment import generate_telemetry, train_models, world_for
    df = generate_telemetry(S05, [1, 2, 3], [0.2], 2000)
    d = str(tmp_path_factory.mktemp('m'))
    return df, d, train_models(df, d, [3], world_for(S05))


def test_telemetry_matches_true_delay(trained):
    from src.experiment import world_for
    df, _, _ = trained
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


@pytest.mark.parametrize('policy', ['model-nom', 'model-cal', 'kdn', 'kdn-greedy', 'model-cal-greedy'])
def test_model_policies_conserve_resources(trained, policy):
    from src.environment import Simulation
    from src.experiment import policy_rng, world_for
    from src.policies import build_policy
    _, d, _ = trained
    w = world_for(S05)
    g = w.build_graph()
    sched, _ = w.schedule('train', 5, 0.3, 1500)
    sim = Simulation(w, g, build_policy(policy, w, policy_rng(5, 0.3, 'train'), models_dir=d), sched)
    sim.run(until=1500)
    assert sum(r.accepted for r in sim.records) > 0
    sim.env.run(until=1500 + w.cfg['max_duration'] + 1)
    for n in g.nodes:
        assert g.nodes[n]['cpu_capacity'] == g.nodes[n]['cpu_max'] and abs(g.nodes[n]['load']) < 1e-9


def test_model_selector_prediction_is_exact_with_true_parameters(trained):
    """With kappa_hat = true kappa and u0_hat * r matching, model-cal reproduces the true processing delay."""
    from src.experiment import policy_rng, world_for
    from src.policies import build_policy
    _, d, _ = trained
    w = world_for(S05)
    g = w.build_graph()
    sel = build_policy('model-cal', w, policy_rng(1, 0.2, 'train'), models_dir=d)
    sched, _ = w.schedule('train', 1, 0.2, 300)
    req = sched[0].request
    req.hidden['r'] = [sel.u0_hat / w.cfg['u0']] * len(req.chain)
    c = sel.candidates(g, req)[0]
    assert sel.predict(g, req, c) == pytest.approx(w.processing_delay(g, c, req), rel=1e-9)
