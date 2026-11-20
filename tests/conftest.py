import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

needs_data = pytest.mark.skipif(not os.path.exists('data/external/sndlib/abilene.txt'),
                                reason='run scripts/fetch_data.sh first')
S0, S05, S1 = 'experiments/envs/s0.json', 'experiments/envs/s05.json', 'experiments/envs/s1.json'
