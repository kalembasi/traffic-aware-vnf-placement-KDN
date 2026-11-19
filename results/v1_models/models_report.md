# v1 KDN models: honest model-level evaluation

## Gatekeeper classifier

| split         | model                     |   accuracy |   precision |   recall |    f1 |   roc_auc |
|:--------------|:--------------------------|-----------:|------------:|---------:|------:|----------:|
| random (v1)   | majority                  |      0.595 |       0.000 |    0.000 | 0.000 |     0.500 |
| random (v1)   | tree-depth2(sfc,free_cpu) |      0.829 |       0.714 |    0.960 | 0.819 |     0.910 |
| random (v1)   | logistic                  |      0.927 |       0.918 |    0.900 | 0.909 |     0.976 |
| random (v1)   | xgboost (v1)              |      0.935 |       0.925 |    0.913 | 0.919 |     0.987 |
| chronological | majority                  |      0.575 |       0.000 |    0.000 | 0.000 |     0.500 |
| chronological | tree-depth2(sfc,free_cpu) |      0.815 |       0.701 |    0.985 | 0.819 |     0.912 |
| chronological | logistic                  |      0.930 |       0.918 |    0.918 | 0.918 |     0.979 |
| chronological | xgboost (v1)              |      0.926 |       0.909 |    0.919 | 0.914 |     0.986 |

## Latency regressor (accepted requests only)

| split         | model               |   rmse |    mae |     r2 |
|:--------------|:--------------------|-------:|-------:|-------:|
| random (v1)   | mean                | 20.312 | 16.230 | -0.000 |
| random (v1)   | linear(action only) |  9.991 |  7.182 |  0.758 |
| random (v1)   | linear(all)         |  9.919 |  7.034 |  0.762 |
| random (v1)   | xgboost (v1)        |  9.389 |  5.898 |  0.786 |
| chronological | mean                | 20.874 | 16.492 | -0.001 |
| chronological | linear(action only) | 10.228 |  7.112 |  0.760 |
| chronological | linear(all)         | 10.139 |  6.966 |  0.764 |
| chronological | xgboost (v1)        |  9.466 |  5.868 |  0.794 |

## Feature contributions of deployed models (mean |SHAP|, gain share)

| model      | feature                  |   mean_abs_shap |   gain_share |
|:-----------|:-------------------------|----------------:|-------------:|
| classifier | network_free_cpu         |           4.551 |        0.412 |
| classifier | sfc_type_encoded         |           2.277 |        0.564 |
| classifier | network_free_bw          |           0.280 |        0.013 |
| classifier | net_bottleneck_bw        |           0.193 |        0.012 |
| classifier | network_active_nodes     |           0.000 |        0.000 |
| classifier | net_max_node_utilization |           0.000 |        0.000 |
| regressor  | action_max_path_distance |          13.733 |        0.696 |
| regressor  | action_num_unique_nodes  |           4.309 |        0.218 |
| regressor  | sfc_type_encoded         |           1.363 |        0.034 |
| regressor  | net_bottleneck_bw        |           0.940 |        0.011 |
| regressor  | network_free_bw          |           0.798 |        0.011 |
| regressor  | network_free_cpu         |           0.452 |        0.010 |
| regressor  | net_max_node_utilization |           0.074 |        0.010 |
| regressor  | network_active_nodes     |           0.013 |        0.009 |

## Decision quality inside the simulator (lambda=0.2, 10 seeds, after warm-up)

```json
{
  "decisions": 8263,
  "decisions_with_distinct_candidate_latencies": 7920,
  "share_distinct": 0.9584896526685224,
  "picked_true_min_all": 0.8259711969018516,
  "picked_true_min_when_distinct": 0.8184343434343434,
  "mean_regret_ms_all": 1.5794505627496067,
  "mean_regret_ms_when_distinct": 1.6478535353535353,
  "median_spearman_pred_vs_true_when_distinct": 0.8944271909999159
}
```

## Gatekeeper decisions vs Greedy-feasibility (10 seeds, after warm-up)

false_reject_share = share of gate rejections that first-fit could have placed;
missed_feasible_rate = share of all requests rejected by the gate although feasible.

|   lambda | sfc_type   |   requests |   gate_reject_rate |   feasible_rate |   false_reject_share |   missed_feasible_rate |   acceptance |
|---------:|:-----------|-----------:|-------------------:|----------------:|---------------------:|-----------------------:|-------------:|
|    0.100 | Video      |       2924 |              0.366 |           0.616 |                0.148 |                  0.054 |        0.591 |
|    0.100 | VoIP       |       2890 |              0.178 |           0.748 |                0.047 |                  0.008 |        0.764 |
|    0.100 | Web        |       3026 |              0.032 |           0.934 |                0.010 |                  0.000 |        0.933 |
|    0.200 | Video      |       5763 |              0.752 |           0.231 |                0.074 |                  0.056 |        0.201 |
|    0.200 | VoIP       |       5797 |              0.483 |           0.399 |                0.031 |                  0.015 |        0.426 |
|    0.200 | Web        |       5924 |              0.127 |           0.787 |                0.032 |                  0.004 |        0.783 |
|    0.400 | Video      |      11643 |              0.904 |           0.063 |                0.023 |                  0.020 |        0.054 |
|    0.400 | VoIP       |      11724 |              0.724 |           0.171 |                0.018 |                  0.013 |        0.187 |
|    0.400 | Web        |      11803 |              0.277 |           0.585 |                0.027 |                  0.008 |        0.578 |
