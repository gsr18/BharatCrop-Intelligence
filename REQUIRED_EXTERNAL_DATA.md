# Required external data assets

These assets are intentionally not stored in Git because of GitHub/LFS size limits or because they are large research archives. The backend expects them at the listed repository-relative paths; provide them through Render persistent storage, an object store sync, or a deployment-time download before starting the API.

| Path | Approx. size | Needed for |
|---|---:|---|
| `phase3b_weather_intelligence/data/processed/weather_features_v1/weather-features-v1/` | ~2.09 GB | WI-05 district archive rainfall forecast (`/api/v1/weather-ml/rainfall-forecast/district*`) |
| `data/raw/india_district_boundaries/91/DISTRICT_BOUNDARY.shp` | ~174 MB | Rebuilding district-to-grid mapping; runtime uses precomputed `models/weather_ml/district_grid_cells_v1.csv` |
| `phase3b_weather_intelligence/reports/weather_intelligence_v2/WI_06_temperature_model_development/` | >1 GB incl. >100 MB joblib/parquet candidates | Future temperature forecasting research only; not used by current endpoints |
| `phase2d_expanded_yield_forecasting/artifacts/` | ~308 MB | Phase 2D research exports/backups; not used by the served API |
| `data/processed/weather_regional/apy_weather_integrated_exploratory.csv` | ~116 MB | Stored in Git LFS; Render must fetch LFS objects or mount this file |

If Git LFS is unavailable on the host, replace the LFS-tracked CSV with an externally hosted copy at the same path and set the documented environment/config overrides if added later.
