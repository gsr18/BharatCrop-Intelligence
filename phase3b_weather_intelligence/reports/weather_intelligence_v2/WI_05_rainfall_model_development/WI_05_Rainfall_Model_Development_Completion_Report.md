# WI-05 — Rainfall Model Development

**Project:** BharatCrop Intelligence  
**Work item:** WI-05  
**Status:** Model development and validation completed; final model selection pending WI-07  
**Target:** PRECTOTCORR (daily rainfall, mm/day)  
**Forecast horizons:** T+1 through T+7  
**Evaluation:** Validation period 2020–2022  
**Final holdout:** 2023–2024 — not accessed

---

## 1. Objective and scope

WI-05 develops and evaluates rainfall forecasting candidates for seven
forecast horizons, from one to seven days ahead.

The work is conducted at grid-cell level using the weather feature dataset.
It is independent of crop-yield modelling and APY data.

The purpose is to compare candidate rainfall models against established
forecasting baselines and understand their performance across seasons,
rainfall-intensity bands, and heavy-rainfall events.

## 2. Data and validation design

- Source dataset: weather-daily-v1.
- Feature dataset: weather-features-v1.
- Spatial resolution: grid-cell level.
- Training target dates: 2013–2019.
- Validation target dates: 2020–2022.
- Final holdout target dates: 2023–2024.
- Training sample used for candidate development: 352,800 rows per horizon.
- Predictor count: 53.
- Rainfall target: PRECTOTCORR, measured in mm/day.
- Wet-day threshold used for classification: 1.0 mm/day.

The split is based on target dates rather than random row assignment.
The final holdout was not accessed during this work.

## 3. Modelling approach

The principal candidate approach is a two-stage model:

1. A HistGradientBoostingClassifier estimates whether rainfall reaches
   the wet-day threshold.
2. A HistGradientBoostingRegressor estimates rainfall amount conditional
   on the wet-day stage.

The candidate models were developed independently for T+1 through T+7.

The wet-day threshold is an operational modelling threshold and should
not be interpreted as a universal meteorological definition.

Model selection remains provisional. Final model comparison and selection
belong to WI-07.

## 4. Seven-horizon validation comparison

horizon  candidate_mae  candidate_rmse  persistence_mae  persistence_rmse  climatology_mae  climatology_rmse  seasonal_naive_mae  seasonal_naive_rmse  mae_improvement_vs_persistence_pct  rmse_improvement_vs_persistence_pct  mae_improvement_vs_climatology_pct  rmse_improvement_vs_climatology_pct  strongest_baseline_mae  strongest_baseline_rmse  mae_rank  rmse_rank
    T+1         3.1016          7.6624           3.2361            9.2107           3.7649             9.062              4.8002              12.1503                              4.1562                              16.8098                             17.6180                              15.4447                  3.2361                    9.062         1          1
    T+2         3.4180          8.3131           4.0844           10.8430           3.7649             9.062              4.7911              12.1318                             16.3157                              23.3321                              9.2141                               8.2642                  3.7649                    9.062         1          1
    T+3         3.5790          8.5520           4.3918           11.3489           3.7649             9.062              4.8055              12.1839                             18.5072                              24.6447                              4.9377                               5.6279                  3.7649                    9.062         1          1
    T+4         3.6100          8.5761           4.5194           11.5325           3.7649             9.062              4.8382              12.2575                             20.1221                              25.6354                              4.1143                               5.3620                  3.7649                    9.062         1          1
    T+5         3.6327          8.5980           4.6048           11.6422           3.7649             9.062              4.8639              12.3194                             21.1106                              26.1480                              3.5114                               5.1203                  3.7649                    9.062         1          1
    T+6         3.6504          8.6190           4.6495           11.6799           3.7649             9.062              4.8695              12.3261                             21.4883                              26.2066                              3.0412                               4.8885                  3.7649                    9.062         1          1
    T+7         3.9909          8.8456           4.6772           11.6909           3.7649             9.062              4.8473              12.2411                             14.6733                              24.3377                             -6.0028                               2.3880                  3.7649                    9.062         2          1

The candidate models outperform the persistence baseline on aggregate
MAE across all seven horizons. However, the strongest baseline differs
by horizon. Climatology is the strongest MAE baseline from T+2 through
T+7, while persistence is strongest at T+1.

At T+7, the candidate has worse aggregate MAE than climatology, despite
better RMSE. This trade-off must be considered during WI-07.

## 5. Seasonal performance

The seasonal evaluation contains 28 records: seven horizons across
four seasons.

horizon       season  observations  actual_mean  candidate_mean  candidate_mae  candidate_rmse  persistence_mae  persistence_rmse  mae_improvement_pct  rmse_improvement_pct
    T+1      Monsoon      922320.0       7.4632          8.0725         5.5297         10.1052           5.7230           11.9479               3.3764               15.4226
    T+1 Post-monsoon      461160.0       3.4938          3.5830         2.8434          7.5010           3.0325            9.1898               6.2346               18.3769
    T+1  Pre-monsoon      695520.0       2.3632          2.2637         2.0770          6.4230           2.1497            7.8577               3.3840               18.2582
    T+1       Winter      682920.0       1.0597          0.9158         1.0403          4.4186           1.1215            5.5139               7.2392               19.8644
    T+2      Monsoon      922320.0       7.4632          7.3988         6.0049         11.0336           7.1626           14.2120              16.1635               22.3646
    T+2 Post-monsoon      461160.0       3.4938          3.2193         3.2375          8.1709           3.9456           10.9348              17.9485               25.2758
    T+2  Pre-monsoon      695520.0       2.3632          2.0625         2.2427          6.8632           2.6680            8.9853              15.9425               23.6174
    T+2       Winter      682920.0       1.0597          0.8995         1.2433          4.6924           1.4634            6.3033              15.0410               25.5560
    T+3      Monsoon      922320.0       7.4632          7.4374         6.2606         11.4147           7.6518           14.9215              18.1814               23.5015
    T+3 Post-monsoon      461160.0       3.4938          3.2523         3.4204          8.3516           4.3059           11.4552              20.5646               27.0929
    T+3  Pre-monsoon      695520.0       2.3632          2.0623         2.3538          7.0095           2.8625            9.3265              17.7707               24.8433
    T+3       Winter      682920.0       1.0597          0.9061         1.3124          4.7614           1.6047            6.5566              18.2142               27.3808
    T+4      Monsoon      922320.0       7.4632          7.4088         6.3105         11.4523           7.8275           15.1516              19.3804               24.4154
    T+4 Post-monsoon      461160.0       3.4938          3.1608         3.4101          8.3349           4.4675           11.6606              23.6688               28.5209
    T+4  Pre-monsoon      695520.0       2.3632          2.0666         2.4015          7.0452           2.9678            9.5171              19.0811               25.9729
    T+4       Winter      682920.0       1.0597          0.8992         1.3285          4.7809           1.6670            6.6158              20.3026               27.7344
    T+5      Monsoon      922320.0       7.4632          7.3973         6.3523         11.4976           7.9479           15.2588              20.0758               24.6494
    T+5 Post-monsoon      461160.0       3.4938          3.1573         3.4263          8.3296           4.5691           11.7671              25.0121               29.2130
    T+5  Pre-monsoon      695520.0       2.3632          2.0554         2.4107          7.0472           3.0159            9.5931              20.0657               26.5381
    T+5       Winter      682920.0       1.0597          0.9042         1.3437          4.7964           1.7320            6.8183              22.4198               29.6532
    T+6      Monsoon      922320.0       7.4632          7.4079         6.3869         11.5333           8.0410           15.2946              20.5700               24.5924
    T+6 Post-monsoon      461160.0       3.4938          3.1832         3.4493          8.3413           4.6181           11.7327              25.3092               28.9051
    T+6  Pre-monsoon      695520.0       2.3632          2.0458         2.4147          7.0596           3.0112            9.6508              19.8098               26.8499
    T+6       Winter      682920.0       1.0597          0.9075         1.3488          4.8012           1.7590            6.9271              23.3187               30.6905
    T+7      Monsoon      922320.0       7.4632          8.9581         7.1642         11.8032           8.0860           15.3398              11.3994               23.0551
    T+7 Post-monsoon      461160.0       3.4938          3.7627         3.7728          8.6088           4.6528           11.6688              18.9146               26.2234
    T+7  Pre-monsoon      695520.0       2.3632          2.1558         2.5925          7.2101           3.0216            9.6906              14.2010               25.5973
    T+7       Winter      682920.0       1.0597          0.6941         1.2766          5.0297           1.7763            6.8830              28.1296               26.9255

Seasonal performance is not uniform. The results should be considered
alongside aggregate metrics rather than treated as evidence that the
candidate is equally reliable in every season.

## 6. Rainfall-intensity performance

The intensity evaluation contains 35 records across seven horizons
and five rainfall-intensity bands.

horizon intensity_band  observations  observation_pct  candidate_mae  persistence_mae  mae_improvement_pct
    T+1     Below 1 mm       1603478          58.0566         0.8887           0.5803             -53.1426
    T+1         1-5 mm        575375          20.8324         3.9714           3.3185             -19.6745
    T+1        5-20 mm        458822          16.6124         4.7967           7.2234              33.5953
    T+1       20-50 mm        105268           3.8114        15.5755          17.5913              11.4588
    T+1         50+ mm         18977           0.6871        53.5433          49.1145              -9.0172
    T+2     Below 1 mm       1603478          58.0566         1.2528           1.0876             -15.1954
    T+2         1-5 mm        575375          20.8324         3.3881           4.3578              22.2518
    T+2        5-20 mm        458822          16.6124         5.0219           8.1743              38.5656
    T+2       20-50 mm        105268           3.8114        19.1217          20.5874               7.1193
    T+2         50+ mm         18977           0.6871        61.3879          58.5887              -4.7777
    T+3     Below 1 mm       1603478          58.0566         1.4147           1.3609              -3.9584
    T+3         1-5 mm        575375          20.8324         3.3974           4.6158              26.3952
    T+3        5-20 mm        458822          16.6124         5.1705           8.4204              38.5958
    T+3       20-50 mm        105268           3.8114        19.9522          21.4747               7.0897
    T+3         50+ mm         18977           0.6871        62.6588          61.5446              -1.8105
    T+4     Below 1 mm       1603478          58.0566         1.4594           1.4983               2.5931
    T+4         1-5 mm        575375          20.8324         3.3988           4.6978              27.6512
    T+4        5-20 mm        458822          16.6124         5.1547           8.4867              39.2614
    T+4       20-50 mm        105268           3.8114        19.9814          21.7201               8.0053
    T+4         50+ mm         18977           0.6871        63.5643          63.0502              -0.8155
    T+5     Below 1 mm       1603478          58.0566         1.4891           1.5874               6.1910
    T+5         1-5 mm        575375          20.8324         3.3725           4.7721              29.3283
    T+5        5-20 mm        458822          16.6124         5.1838           8.5068              39.0635
    T+5       20-50 mm        105268           3.8114        20.1237          22.0192               8.6085
    T+5         50+ mm         18977           0.6871        63.6622          63.5390              -0.1940
    T+6     Below 1 mm       1603478          58.0566         1.5092           1.6426               8.1237
    T+6         1-5 mm        575375          20.8324         3.3832           4.7521              28.8052
    T+6        5-20 mm        458822          16.6124         5.1946           8.5626              39.3339
    T+6       20-50 mm        105268           3.8114        20.1440          22.1830               9.1916
    T+6         50+ mm         18977           0.6871        63.8456          63.7419              -0.1626
    T+7     Below 1 mm       1603478          58.0566         1.6751           1.6816               0.3904
    T+7         1-5 mm        575375          20.8324         5.0569           4.7761              -5.8794
    T+7        5-20 mm        458822          16.6124         4.9067           8.5434              42.5678
    T+7       20-50 mm        105268           3.8114        18.8910          22.3009              15.2902
    T+7         50+ mm         18977           0.6871        62.5509          63.5597               1.5871

The candidate's aggregate performance does not imply consistent
performance across rainfall intensities. In particular, performance
in the lower rainfall bands and the highest intensity band requires
separate consideration.

## 7. Heavy-rainfall diagnostics

Heavy rainfall is evaluated here using the 50+ mm/day band.

horizon  observations  actual_mean  candidate_mean  persistence_mean  candidate_bias  persistence_bias  candidate_mae  persistence_mae  candidate_rmse  persistence_rmse  actual_p95  candidate_p95  persistence_p95  actual_max  candidate_max  persistence_max  candidate_mae_improvement_pct  candidate_rmse_improvement_pct  candidate_mean_underestimation_mm
    T+1         18977      77.4719         25.4038           36.1843        -52.0681          -41.2876        53.5433          49.1145         65.4931           63.0324     142.498        64.8912          101.742      666.37       192.9811           508.00                        -9.0172                         -3.9038                            52.0681
    T+2         18977      77.4719         16.4462           22.6844        -61.0257          -54.7875        61.3879          58.5887         72.4713           71.5838     142.498        47.3190           74.786      666.37       147.5116           666.37                        -4.7777                         -1.2398                            61.0257
    T+3         18977      77.4719         15.2398           18.2526        -62.2321          -59.2193        62.6588          61.5446         73.5146           73.5814     142.498        47.0082           65.622      666.37       157.4192           440.85                        -1.8105                          0.0908                            62.2321
    T+4         18977      77.4719         14.1108           16.9983        -63.3611          -60.4736        63.5643          63.0502         74.2442           75.0987     142.498        39.2729           60.376      666.37       116.2748           440.85                        -0.8154                          1.1378                            63.3611
    T+5         18977      77.4719         14.0348           16.2209        -63.4371          -61.2510        63.6622          63.5390         74.2972           75.4105     142.498        40.0633           59.514      666.37       122.1049           410.05                        -0.1939                          1.4763                            63.4371
    T+6         18977      77.4719         13.8285           16.1630        -63.6434          -61.3089        63.8456          63.7419         74.4223           75.4055     142.498        38.3718           59.244      666.37       118.1988           383.40                        -0.1627                          1.3039                            63.6434
    T+7         18977      77.4719         15.2407           16.0553        -62.2312          -61.4166        62.5509          63.5597         73.3555           75.1474     142.498        40.7244           58.392      666.37       134.7834           464.93                         1.5872                          2.3845                            62.2312

The heavy-rainfall results reveal a major limitation:

- The actual mean rainfall in this band is approximately 77.47 mm/day.
- Candidate mean predictions are substantially lower across all horizons.
- Candidate heavy-band MAE is worse than persistence from T+1 through T+6.
- At T+7, candidate MAE improves on persistence by only approximately
  1.59%.
- Candidate predictions substantially underestimate heavy-rainfall
  intensity.

Therefore, these candidates should not be represented as validated
heavy-rainfall warning models.

## 8. Wet-day classification diagnostics

Detailed classifier threshold and calibration diagnostics were evaluated
for T+1.

At the 0.40 classification threshold:

- Precision: 0.8088
- Recall: 0.8654
- F1-score: 0.8361
- PR-AUC: 0.9147
- Brier score: 0.099175

The 0.40 threshold produced the best F1-score among the tested thresholds.
It remains a provisional operating threshold.

These classification results should not be generalized to T+2 through
T+7 without equivalent horizon-specific evaluation.

## 9. Key limitations

1. **Heavy-rainfall underestimation:** Candidate models substantially
   underestimate rainfall in the 50+ mm/day band.
2. **Uneven intensity performance:** Aggregate metrics conceal weaknesses
   in specific rainfall-intensity bands.
3. **T+7 aggregate trade-off:** T+7 candidate MAE is worse than climatology.
4. **Sampling:** Candidate development used a 352,800-row sample per
   horizon rather than the full feature-complete training dataset.
5. **Spatial scope:** Evaluation is grid-cell level; district-level
   aggregation and land masking are outside this work item's scope.
6. **Historical data limitation:** The source archive ends in 2024 and
   does not provide live weather forecasts.
7. **Agricultural interpretation:** Weather predictions alone do not
   establish crop damage, disease occurrence, or yield loss.
8. **Holdout:** The final 2023–2024 holdout remains untouched and requires
   a separately controlled evaluation.

## 10. Handoff to WI-07

WI-05 provides seven horizon-specific rainfall candidate models and
validation evidence for final comparison.

WI-07 must:

- Compare candidates consistently against WI-04 baselines.
- Review aggregate MAE and RMSE together.
- Consider seasonal and intensity-band performance.
- Explicitly assess heavy-rainfall underestimation.
- Decide whether one model family is suitable across all horizons or
  whether horizon-specific choices are justified.
- Preserve the final holdout for controlled evaluation after model
  selection decisions are complete.

No final production model is selected by WI-05.

## 11. Completion statement

WI-05 rainfall model development and validation diagnostics for T+1
through T+7 have been consolidated.

The work item is ready for handoff to WI-07 for model comparison and
final selection, subject to review of the documented limitations.

**Final holdout accessed: No.**