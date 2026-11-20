# Data ablation (sigma = 1, 30 test seeds)

Mean latency gain of oracle-greedy over smart (ms; positive = oracle-greedy faster).

| variant | λ=0.02 | λ=0.05 | λ=0.1 | λ=0.2 | λ=0.4 |
|---|---|---|---|---|---|
| base | +4.63 | +3.39 | +0.41 | -0.76 | -0.81 |
| noKDN | +4.46 | +3.20 | +0.26 | -0.78 | -0.62 |
| noTM | +5.01 | +3.31 | -0.10 | -1.10 | -0.70 |
| neither | +4.85 | +3.15 | -0.18 | -1.04 | -0.69 |

Largest change vs base: 0.58 ms.
