# Phase 3B Weather Intelligence: Stage 2

This workspace contains a reproducible, weather-only daily panel and reusable feature preparation. It reads the original NASA POWER / MERRA-2 regional JSON archive at `data/raw/weather_regional`. It does not import agricultural or yield services, read APY data, train models, or change the existing application.

## Build

From this workspace, install the pinned requirements into a dedicated environment and run the complete audit and build:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\scripts\build_weather_dataset.py run
```

The `audit` command validates every expected source file and writes the immutable source manifest and quality report. The `build` command verifies the manifest and each source hash, then writes the canonical Parquet dataset. `run` executes both stages. Existing immutable manifests and versioned datasets are never silently replaced: a content mismatch stops the pipeline.

## Dataset

The canonical row key is `(cell_id, date)`. Coordinates are sorted by latitude then longitude and assigned `cell_0000` through `cell_2519`. `date` is a UTC calendar date stored as Arrow `date32`, not a local timestamp. The panel contains the three weather measurements as float64 values, per-variable archive region, original source tags, and units, plus row-level quality flags. The manifest retains every source file's relative path, SHA-256, complete source header, parameter metadata, date range, region identifier, and size.

The audited contract is 2,016 regional JSON files, 2,520 grid cells, and 4,383 dates per cell from 2013-01-01 through 2024-12-31: 11,045,160 canonical rows and 33,135,480 source measurements. T2M_MAX and T2M_MIN retain `MERRA2` and `POWER` tags; PRECTOTCORR retains `MERRA2`. These tags are never collapsed into a single source label. The archived `Rnnn` identifiers are retained as source grouping metadata and are not treated as districts.

Parquet is partitioned deterministically into one Zstandard-compressed file per calendar year under `data/processed/weather_daily_v1/year=YYYY/`. The builder stages output under a temporary sibling directory and atomically publishes the completed dataset. It stores no second full-size CSV or materialized feature panel. `dataset_metadata.json` records the row and cell counts, partition hashes and sizes, manifest and config hashes, full canonical and feature schemas, quality summary, dependency versions, and Parquet settings.

## Feature preparation

Reusable functions live in `src/weather_intelligence/features.py` and operate on a weather-only pandas DataFrame with one consecutive UTC date per cell:

- Temperature range: `T2M_RANGE = T2M_MAX - T2M_MIN`.
- Prediction lags: for a next-day target, lag 1 is the as-of-date observation; lags 2, 3, 7, 14, and 30 use observations that many calendar days before the target date.
- Prediction rolling statistics: trailing 3, 7, 14, and 30-day means and sample standard deviations (`ddof=1`) for T2M_MAX, T2M_MIN, PRECTOTCORR, and T2M_RANGE. Windows include the as-of date, require a complete window, and are grouped by cell.
- Precipitation history: trailing sums and wet-day counts/fractions for the same windows. A wet day is PRECTOTCORR >= 1.0 mm/day by default.
- Calendar features: sine and cosine of day of year using a 365.2425-day period.
- Retrospective descriptive features: daily descriptors, completed calendar-month summaries, and fixed month-bin weather-season summaries. The configured bins are winter Jan-Feb, pre-monsoon Mar-May, monsoon Jun-Sep, and post-monsoon Oct-Dec; these are weather-analysis bins, not agricultural seasons.

Prediction rows contain the as-of date, next target date, and next-day T2M_MAX and PRECTOTCORR targets. Target values are created by a one-row lead within each cell and are not included in feature calculations. All lags and trailing windows use only the as-of date or earlier. Retrospective monthly and seasonal summaries intentionally use every observation in the completed period and must not be passed into a prediction task before that period ends. No centered windows are used.

The feature functions are reusable for a selected set of cells or a bounded in-memory frame. The canonical source remains partitioned on disk; this stage does not create a redundant full-size feature copy.

## Validation and reproducibility

The full archive audit fails closed if file count, headers, parameter keys, source tags, units, dates, grid cells, coordinate-to-region mapping, or any audited value check differs from the Stage 1 contract. It checks missing/duplicate keys, fill sentinel `-999`, non-finite or non-numeric values, negative precipitation, and T2M_MIN > T2M_MAX. It does not impute, drop, or silently repair observations. Each accepted manifest is content-addressed and immutable.

Configuration is `config/pipeline_v1.json`; exact package pins are in `requirements.txt` and `pyproject.toml`. The generated `schemas/weather_feature_schema_v1.json` states the feature formulas and prediction-time availability rules. `reports/runtime_benchmark.json` records command, UTC start time, elapsed time, peak process working set, output summaries, and Python/numpy/pandas/PyArrow versions.

Run the tests from this workspace after building the archive:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The suite exercises date parsing, malformed and duplicate JSON, missing records, source metadata, sentinel and numeric validation, cross-cell window isolation, future-perturbation leakage checks, deterministic feature output, and a full re-scan of the 2,016-file weather archive against the generated Parquet metadata.

## Workspace layout

```text
config/pipeline_v1.json
manifests/source_manifest_v1.json
reports/source_quality_v1.json
reports/runtime_benchmark.json
schemas/weather_feature_schema_v1.json
data/processed/weather_daily_v1/
src/weather_intelligence/
scripts/build_weather_dataset.py
tests/
```
