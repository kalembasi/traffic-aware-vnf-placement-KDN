import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)


@pytest.fixture
def config():
    with open(os.path.join(ROOT, 'config', 'config.json')) as f:
        return json.load(f)


V1_MODELS = os.path.join(ROOT, 'models', 'v1')
has_v1_models = os.path.exists(os.path.join(V1_MODELS, 'kdn_regressor.json'))
