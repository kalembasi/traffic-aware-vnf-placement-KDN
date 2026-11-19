# v1 reproduction (course report protocol)

Mean ± sample std over seeds (95% CI half-width in brackets).

## lambda = 0.2

| Algorithm | Seeds | Acceptance (%) | CPU-weighted acc. (%) | Latency mean (ms) | Latency p95 (ms) | Active nodes | Decision (ms) |
|---|---|---|---|---|---|---|---|
| greedy | 5 | 54.62 ± 6.71 [8.33] | 48.17 ± 7.36 [9.14] | 20.52 ± 5.29 [6.57] | 55.12 ± 16.88 [20.96] | 11.24 ± 0.17 [0.21] | 0.013 ± 0.001 [0.002] |
| smart | 5 | 53.39 ± 7.86 [9.75] | 47.23 ± 8.11 [10.07] | 8.56 ± 2.26 [2.80] | 34.22 ± 4.49 [5.58] | 11.25 ± 0.18 [0.23] | 0.039 ± 0.005 [0.006] |
| kdn | 5 | 54.44 ± 6.37 [7.92] | 47.51 ± 7.20 [8.94] | 12.68 ± 2.14 [2.66] | 40.39 ± 6.31 [7.84] | 11.43 ± 0.16 [0.19] | 0.349 ± 0.018 [0.023] |
