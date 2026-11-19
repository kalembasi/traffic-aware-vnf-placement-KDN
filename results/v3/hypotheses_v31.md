# v3.1 addendum (Holm across the 20 sigma x lambda cells per comparison)

| hypothesis          |   sigma |   lambda | comparison                     |   mean_diff |   ci95_lo |   ci95_hi |   n_lower |   n_higher |           p |      p_holm | result                    |
|:--------------------|--------:|---------:|:-------------------------------|------------:|----------:|----------:|----------:|-----------:|------------:|------------:|:--------------------------|
| H5                  |    0    |     0.02 | kdn3-greedy - smart-load       |  -0.3015    | -0.368    |  -0.2351  |        29 |          1 |   1.991e-06 |   2.589e-05 | kdn3-greedy better        |
| H5                  |    0    |     0.05 | kdn3-greedy - smart-load       |  -0.2538    | -0.3717   |  -0.1359  |        26 |          4 |   6.287e-05 |   0.0006915 | kdn3-greedy better        |
| H5                  |    0    |     0.1  | kdn3-greedy - smart-load       |  -0.1452    | -0.3146   |   0.02415 |        18 |         12 |   0.1048    |   0.7339    | no significant difference |
| H5                  |    0    |     0.2  | kdn3-greedy - smart-load       |   0.1625    | -0.04902  |   0.3739  |        12 |         18 |   0.06356   |   0.572     | no significant difference |
| H5                  |    0    |     0.4  | kdn3-greedy - smart-load       |   0.01676   | -0.1775   |   0.2111  |        13 |         17 |   0.8553    |   1         | no significant difference |
| H5                  |    0.25 |     0.02 | kdn3-greedy - smart-load       |  -0.7206    | -0.8163   |  -0.625   |        29 |          1 |   3.725e-09 |   6.333e-08 | kdn3-greedy better        |
| H5                  |    0.25 |     0.05 | kdn3-greedy - smart-load       |  -0.2931    | -0.4114   |  -0.1748  |        23 |          7 |   4.408e-05 |   0.0005289 | kdn3-greedy better        |
| H5                  |    0.25 |     0.1  | kdn3-greedy - smart-load       |   0.08301   | -0.1209   |   0.287   |        12 |         18 |   0.44      |   1         | no significant difference |
| H5                  |    0.25 |     0.2  | kdn3-greedy - smart-load       |  -0.02474   | -0.1853   |   0.1358  |        13 |         17 |   0.9354    |   1         | no significant difference |
| H5                  |    0.25 |     0.4  | kdn3-greedy - smart-load       |   0.3976    |  0.158    |   0.6372  |         9 |         21 |   0.001719  |   0.01719   | smart-load better         |
| H5                  |    0.5  |     0.02 | kdn3-greedy - smart-load       |  -1.596     | -1.726    |  -1.465   |        30 |          0 |   1.863e-09 |   3.725e-08 | kdn3-greedy better        |
| H5                  |    0.5  |     0.05 | kdn3-greedy - smart-load       |  -0.7854    | -0.9609   |  -0.6099  |        27 |          3 |   4.657e-08 |   6.519e-07 | kdn3-greedy better        |
| H5                  |    0.5  |     0.1  | kdn3-greedy - smart-load       |   0.03666   | -0.1676   |   0.2409  |        11 |         19 |   0.3285    |   1         | no significant difference |
| H5                  |    0.5  |     0.2  | kdn3-greedy - smart-load       |   0.1675    | -0.02422  |   0.3593  |        11 |         19 |   0.1048    |   0.7339    | no significant difference |
| H5                  |    0.5  |     0.4  | kdn3-greedy - smart-load       |   0.1669    | -0.007998 |   0.3418  |        13 |         17 |   0.07672   |   0.6138    | no significant difference |
| H5                  |    1    |     0.02 | kdn3-greedy - smart-load       |  -4.487     | -4.84     |  -4.133   |        30 |          0 |   1.863e-09 |   3.725e-08 | kdn3-greedy better        |
| H5                  |    1    |     0.05 | kdn3-greedy - smart-load       |  -2.818     | -3.185    |  -2.45    |        30 |          0 |   1.863e-09 |   3.725e-08 | kdn3-greedy better        |
| H5                  |    1    |     0.1  | kdn3-greedy - smart-load       |  -0.1472    | -0.5115   |   0.2172  |        16 |         14 |   0.4522    |   1         | no significant difference |
| H5                  |    1    |     0.2  | kdn3-greedy - smart-load       |   1.228     |  0.9509   |   1.506   |         1 |         29 |   9.313e-09 |   1.49e-07  | smart-load better         |
| H5                  |    1    |     0.4  | kdn3-greedy - smart-load       |   1.06      |  0.8382   |   1.282   |         2 |         28 |   3.539e-08 |   5.309e-07 | smart-load better         |
| H6                  |    0    |     0.02 | kdn3-greedy - kdn3             |   0.07774   |  0.02597  |   0.1295  |         9 |         21 |   0.006195  |   0.02478   | kdn3 better               |
| H6                  |    0    |     0.05 | kdn3-greedy - kdn3             |   0.05102   | -0.09142  |   0.1935  |        10 |         20 |   0.1642    |   0.3284    | no significant difference |
| H6                  |    0    |     0.1  | kdn3-greedy - kdn3             |  -0.845     | -1.078    |  -0.6119  |        28 |          2 |   6.147e-08 |   6.761e-07 | kdn3-greedy better        |
| H6                  |    0    |     0.2  | kdn3-greedy - kdn3             |  -1.389     | -1.629    |  -1.15    |        29 |          1 |   3.725e-09 |   4.843e-08 | kdn3-greedy better        |
| H6                  |    0    |     0.4  | kdn3-greedy - kdn3             |  -1.635     | -1.807    |  -1.463   |        30 |          0 |   1.863e-09 |   3.725e-08 | kdn3-greedy better        |
| H6                  |    0.25 |     0.02 | kdn3-greedy - kdn3             |  -0.1022    | -0.1585   |  -0.04604 |        23 |          7 |   0.0007296 |   0.003648  | kdn3-greedy better        |
| H6                  |    0.25 |     0.05 | kdn3-greedy - kdn3             |  -0.09955   | -0.2604   |   0.06132 |        15 |         15 |   0.428     |   0.428     | no significant difference |
| H6                  |    0.25 |     0.1  | kdn3-greedy - kdn3             |  -0.6472    | -0.838    |  -0.4564  |        27 |          3 |   1.192e-06 |   8.345e-06 | kdn3-greedy better        |
| H6                  |    0.25 |     0.2  | kdn3-greedy - kdn3             |  -1.542     | -1.752    |  -1.332   |        30 |          0 |   1.863e-09 |   3.725e-08 | kdn3-greedy better        |
| H6                  |    0.25 |     0.4  | kdn3-greedy - kdn3             |  -1.255     | -1.509    |  -1.001   |        29 |          1 |   3.725e-09 |   4.843e-08 | kdn3-greedy better        |
| H6                  |    0.5  |     0.02 | kdn3-greedy - kdn3             |  -0.4242    | -0.4944   |  -0.3539  |        30 |          0 |   1.863e-09 |   3.725e-08 | kdn3-greedy better        |
| H6                  |    0.5  |     0.05 | kdn3-greedy - kdn3             |  -0.3334    | -0.4925   |  -0.1744  |        24 |          6 |   9.903e-05 |   0.0005942 | kdn3-greedy better        |
| H6                  |    0.5  |     0.1  | kdn3-greedy - kdn3             |  -0.7858    | -1.018    |  -0.5533  |        28 |          2 |   1.639e-07 |   1.639e-06 | kdn3-greedy better        |
| H6                  |    0.5  |     0.2  | kdn3-greedy - kdn3             |  -1.055     | -1.249    |  -0.8612  |        30 |          0 |   1.863e-09 |   3.725e-08 | kdn3-greedy better        |
| H6                  |    0.5  |     0.4  | kdn3-greedy - kdn3             |  -1.489     | -1.689    |  -1.289   |        30 |          0 |   1.863e-09 |   3.725e-08 | kdn3-greedy better        |
| H6                  |    1    |     0.02 | kdn3-greedy - kdn3             |  -1.378     | -1.543    |  -1.213   |        30 |          0 |   1.863e-09 |   3.725e-08 | kdn3-greedy better        |
| H6                  |    1    |     0.05 | kdn3-greedy - kdn3             |  -1.369     | -1.58     |  -1.158   |        30 |          0 |   1.863e-09 |   3.725e-08 | kdn3-greedy better        |
| H6                  |    1    |     0.1  | kdn3-greedy - kdn3             |  -0.8826    | -1.14     |  -0.6247  |        26 |          4 |   3.856e-07 |   3.47e-06  | kdn3-greedy better        |
| H6                  |    1    |     0.2  | kdn3-greedy - kdn3             |  -0.3697    | -0.6336   |  -0.1059  |        22 |          8 |   0.009932  |   0.02979   | kdn3-greedy better        |
| H6                  |    1    |     0.4  | kdn3-greedy - kdn3             |  -0.8649    | -1.083    |  -0.6472  |        29 |          1 |   4.712e-07 |   3.77e-06  | kdn3-greedy better        |
| gap-greedy          |    0    |     0.02 | kdn3-greedy - oracle-greedy    |   0.006656  | -0.01599  |   0.0293  |        17 |         13 | nan         | nan         |                           |
| gap-greedy          |    0    |     0.05 | kdn3-greedy - oracle-greedy    |   0.01742   | -0.07889  |   0.1137  |        16 |         14 | nan         | nan         |                           |
| gap-greedy          |    0    |     0.1  | kdn3-greedy - oracle-greedy    |  -0.1171    | -0.3325   |   0.0983  |        19 |         11 | nan         | nan         |                           |
| gap-greedy          |    0    |     0.2  | kdn3-greedy - oracle-greedy    |  -0.01135   | -0.2398   |   0.2171  |        16 |         14 | nan         | nan         |                           |
| gap-greedy          |    0    |     0.4  | kdn3-greedy - oracle-greedy    |  -0.1567    | -0.3485   |   0.03522 |        17 |         13 | nan         | nan         |                           |
| gap-greedy          |    0.25 |     0.02 | kdn3-greedy - oracle-greedy    |   0.02965   | -0.01506  |   0.07437 |        10 |         20 | nan         | nan         |                           |
| gap-greedy          |    0.25 |     0.05 | kdn3-greedy - oracle-greedy    |  -0.03546   | -0.1576   |   0.08669 |        14 |         16 | nan         | nan         |                           |
| gap-greedy          |    0.25 |     0.1  | kdn3-greedy - oracle-greedy    |  -0.02208   | -0.2112   |   0.167   |        17 |         13 | nan         | nan         |                           |
| gap-greedy          |    0.25 |     0.2  | kdn3-greedy - oracle-greedy    |  -0.1383    | -0.3317   |   0.05514 |        20 |         10 | nan         | nan         |                           |
| gap-greedy          |    0.25 |     0.4  | kdn3-greedy - oracle-greedy    |   0.1299    | -0.07226  |   0.3321  |        10 |         20 | nan         | nan         |                           |
| gap-greedy          |    0.5  |     0.02 | kdn3-greedy - oracle-greedy    |  -0.02313   | -0.06129  |   0.01503 |        17 |         13 | nan         | nan         |                           |
| gap-greedy          |    0.5  |     0.05 | kdn3-greedy - oracle-greedy    |  -0.06404   | -0.1704   |   0.04234 |        22 |          8 | nan         | nan         |                           |
| gap-greedy          |    0.5  |     0.1  | kdn3-greedy - oracle-greedy    |  -0.05419   | -0.2274   |   0.119   |        17 |         13 | nan         | nan         |                           |
| gap-greedy          |    0.5  |     0.2  | kdn3-greedy - oracle-greedy    |  -0.06314   | -0.2583   |   0.132   |        15 |         15 | nan         | nan         |                           |
| gap-greedy          |    0.5  |     0.4  | kdn3-greedy - oracle-greedy    |  -0.1069    | -0.3174   |   0.1036  |        16 |         14 | nan         | nan         |                           |
| gap-greedy          |    1    |     0.02 | kdn3-greedy - oracle-greedy    |   0.002887  | -0.06751  |   0.07329 |        18 |         12 | nan         | nan         |                           |
| gap-greedy          |    1    |     0.05 | kdn3-greedy - oracle-greedy    |   0.02773   | -0.1429   |   0.1983  |        15 |         15 | nan         | nan         |                           |
| gap-greedy          |    1    |     0.1  | kdn3-greedy - oracle-greedy    |  -0.05866   | -0.3077   |   0.1904  |        15 |         15 | nan         | nan         |                           |
| gap-greedy          |    1    |     0.2  | kdn3-greedy - oracle-greedy    |   0.22      | -0.03683  |   0.4768  |        14 |         16 | nan         | nan         |                           |
| gap-greedy          |    1    |     0.4  | kdn3-greedy - oracle-greedy    |  -0.1181    | -0.3373   |   0.101   |        19 |         11 | nan         | nan         |                           |
| vs-model-cal-greedy |    0    |     0.02 | kdn3-greedy - model-cal-greedy |   0.01169   | -0.009258 |   0.03264 |        15 |         15 | nan         | nan         |                           |
| vs-model-cal-greedy |    0    |     0.05 | kdn3-greedy - model-cal-greedy |   0.02725   | -0.05071  |   0.1052  |        15 |         15 | nan         | nan         |                           |
| vs-model-cal-greedy |    0    |     0.1  | kdn3-greedy - model-cal-greedy |  -0.1136    | -0.2974   |   0.07012 |        19 |         11 | nan         | nan         |                           |
| vs-model-cal-greedy |    0    |     0.2  | kdn3-greedy - model-cal-greedy |   0.04305   | -0.1472   |   0.2332  |        15 |         15 | nan         | nan         |                           |
| vs-model-cal-greedy |    0    |     0.4  | kdn3-greedy - model-cal-greedy |  -0.05807   | -0.2373   |   0.1212  |        16 |         14 | nan         | nan         |                           |
| vs-model-cal-greedy |    0.25 |     0.02 | kdn3-greedy - model-cal-greedy |   0.01774   | -0.008678 |   0.04416 |        10 |         20 | nan         | nan         |                           |
| vs-model-cal-greedy |    0.25 |     0.05 | kdn3-greedy - model-cal-greedy |  -0.04591   | -0.159    |   0.06718 |        16 |         14 | nan         | nan         |                           |
| vs-model-cal-greedy |    0.25 |     0.1  | kdn3-greedy - model-cal-greedy |   0.01887   | -0.1637   |   0.2014  |        14 |         16 | nan         | nan         |                           |
| vs-model-cal-greedy |    0.25 |     0.2  | kdn3-greedy - model-cal-greedy |  -0.1535    | -0.3383   |   0.03133 |        19 |         11 | nan         | nan         |                           |
| vs-model-cal-greedy |    0.25 |     0.4  | kdn3-greedy - model-cal-greedy |   0.1553    | -0.07719  |   0.3879  |        10 |         20 | nan         | nan         |                           |
| vs-model-cal-greedy |    0.5  |     0.02 | kdn3-greedy - model-cal-greedy |   9.613e-07 | -0.03189  |   0.03189 |        16 |         14 | nan         | nan         |                           |
| vs-model-cal-greedy |    0.5  |     0.05 | kdn3-greedy - model-cal-greedy |  -0.02791   | -0.1396   |   0.08377 |        18 |         12 | nan         | nan         |                           |
| vs-model-cal-greedy |    0.5  |     0.1  | kdn3-greedy - model-cal-greedy |  -0.002028  | -0.1981   |   0.1941  |        16 |         14 | nan         | nan         |                           |
| vs-model-cal-greedy |    0.5  |     0.2  | kdn3-greedy - model-cal-greedy |   0.03542   | -0.1845   |   0.2553  |        14 |         16 | nan         | nan         |                           |
| vs-model-cal-greedy |    0.5  |     0.4  | kdn3-greedy - model-cal-greedy |  -0.05711   | -0.2327   |   0.1184  |        16 |         14 | nan         | nan         |                           |
| vs-model-cal-greedy |    1    |     0.02 | kdn3-greedy - model-cal-greedy |   0.001226  | -0.07553  |   0.07798 |        19 |         11 | nan         | nan         |                           |
| vs-model-cal-greedy |    1    |     0.05 | kdn3-greedy - model-cal-greedy |  -0.04273   | -0.176    |   0.0905  |        17 |         13 | nan         | nan         |                           |
| vs-model-cal-greedy |    1    |     0.1  | kdn3-greedy - model-cal-greedy |  -0.04035   | -0.3405   |   0.2598  |        13 |         17 | nan         | nan         |                           |
| vs-model-cal-greedy |    1    |     0.2  | kdn3-greedy - model-cal-greedy |   0.1522    | -0.1048   |   0.4092  |        16 |         14 | nan         | nan         |                           |
| vs-model-cal-greedy |    1    |     0.4  | kdn3-greedy - model-cal-greedy |  -0.09324   | -0.3123   |   0.1258  |        16 |         14 | nan         | nan         |                           |
