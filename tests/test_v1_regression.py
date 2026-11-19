"""The refactored code must reproduce the per-seed numbers of the original v1 code (course report)."""
import os

import pandas as pd
import pytest

from src.experiment import run_single
from tests.conftest import ROOT, V1_MODELS, has_v1_models

REF = pd.read_csv(os.path.join(ROOT, 'tests', 'fixtures', 'v1_course_report_runs.csv'))
NAMES = {'greedy': 'GreedyPlacement', 'smart': 'SmartPlacement', 'kdn': 'XGBoostPlacement'}


@pytest.mark.parametrize('algo', ['greedy', 'smart',
                                  pytest.param('kdn', marks=pytest.mark.skipif(not has_v1_models,
                                               reason='run ./run_all.sh first (needs models/v1)'))])
@pytest.mark.parametrize('seed', [42, 7, 123, 0, 99])
def test_matches_v1(config, algo, seed):
    row, _ = run_single(config, algo, seed, 0.2, 1000, models_dir=V1_MODELS)
    ref = REF[(REF.Algorithm == NAMES[algo]) & (REF.Seed == seed)].iloc[0]
    assert row['acceptance'] == pytest.approx(ref.Acceptance_Ratio, abs=1e-9)
    assert row['lat_mean'] == pytest.approx(ref.Avg_Latency, abs=1e-9)
    assert row['active_nodes'] == pytest.approx(ref.Avg_Active_Nodes, abs=1e-9)
