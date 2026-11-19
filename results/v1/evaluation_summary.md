# KDN Placement Algorithms - Evaluation Summary

**Seeds:** 42, 7, 123, 0, 99  |  **Runs per algorithm:** 5

## Results (Mean +/- Std)

| Algorithm | Acceptance Ratio | Avg Latency (ms) | Avg Active Nodes |
|-----------|-----------------|-----------------|-----------------|
| GreedyPlacement | 54.62% +/- 6.00% | 20.52 +/- 4.73 | 11.24 +/- 0.15 |
| SmartPlacement | 53.39% +/- 7.03% | 8.56 +/- 2.02 | 11.25 +/- 0.16 |
| XGBoostPlacement | 54.44% +/- 5.70% | 12.68 +/- 1.91 | 11.43 +/- 0.14 |

## Per-Algorithm Breakdown

### GreedyPlacement

| Metric | Mean | Std | Min | Max |
|--------|------|-----|-----|-----|
| Acceptance Ratio (%) | 54.62 | 6.00 | 47.22 | 63.69 |
| Avg Latency (ms)     | 20.52 | 4.73 | 13.88 | 27.61 |
| Avg Active Nodes     | 11.24 | 0.15 | 10.98 | 11.40 |

### SmartPlacement

| Metric | Mean | Std | Min | Max |
|--------|------|-----|-----|-----|
| Acceptance Ratio (%) | 53.39 | 7.03 | 43.98 | 64.25 |
| Avg Latency (ms)     | 8.56 | 2.02 | 6.02 | 11.56 |
| Avg Active Nodes     | 11.25 | 0.16 | 10.97 | 11.43 |

### XGBoostPlacement

| Metric | Mean | Std | Min | Max |
|--------|------|-----|-----|-----|
| Acceptance Ratio (%) | 54.44 | 5.70 | 47.69 | 64.25 |
| Avg Latency (ms)     | 12.68 | 1.91 | 9.23 | 14.76 |
| Avg Active Nodes     | 11.43 | 0.14 | 11.20 | 11.63 |
