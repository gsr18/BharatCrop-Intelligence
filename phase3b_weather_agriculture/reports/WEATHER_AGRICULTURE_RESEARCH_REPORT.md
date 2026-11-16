# Phase 3B — Historical Crop-Region Evidence Explorer

**Status:** Experimental historical evidence feature. It is not a crop-suitability model, a yield forecast, or a causal weather-impact analysis.

## Purpose and scope

The explorer provides district comparisons of historical APY crop performance and a separate historical weather profile where both a sourced crop-calendar mapping and complete daily weather coverage are available. It does not combine yield, weather, consistency, or coverage into a composite score. The existing manual yield-prediction model is not used or changed.

## Data sources and provenance

### APY agricultural observations

The service reads the project’s processed APY-weather integration at `data/processed/weather_regional/apy_weather_integrated_exploratory.csv`. The project data manifest identifies the APY source as UPAg / the Department of Agriculture & Farmers Welfare. The file contains 376,272 rows overall; the existing `APYDataService.valid_frame` quality rules retain 49,645 observations across 2013–2024 for the valid APY population. The dataset declares yield in kg/ha. The API returns the source file and SHA-256 digest for the exact file loaded.

The explorer reuses `APYDataService.valid_frame`; it does not introduce a second APY cleaning policy. Existing exclusions remain in force: aggregate and non-individual crop records, aggregate/unsupported seasons, invalid location/crop values, non-finite or non-positive area, production, or yield, and all four established APY quality-control flags: `QC_AreaZero-ProductionPositive`, `QC_AreaPositive-ProductionZero`, `QC_NegativeMeasurements`, and `QC_PositiveYieldWithoutPositiveAreaProduction`.

### Daily weather

Daily weather comes from the existing NASA POWER Daily API v2.10.1 files under `data/raw/weather_regional/{PRECTOTCORR,T2M_MAX,T2M_MIN}/{year}/`. Their headers identify MERRA2 as the source, UTC as the time standard, and `-999` as the fill value. The raw files contain 56 spatial tiles per variable per year for 2013–2024 (672 files per variable). Parameter metadata gives precipitation in mm/day and two-metre maximum/minimum temperature in degrees Celsius.

These are gridded estimates, not local weather-station observations. The prior annual district weather dataset, `data/processed/weather_regional/district_weather_annual_cleaned_flagged_2013_2024.csv`, is used only for existing district-to-grid coordinates and quality/provenance fields. Its annual values are not treated as within-season weather exposure.

### Crop-calendar evidence

The versioned mapping registry is `phase3b_weather_agriculture/data/crop_calendar_mappings_v1.json`, version 1.0.0. It contains one supported mapping: Punjab, Rice, Kharif, based on Punjab Agricultural University’s [Package of Practices for Crops of Punjab, Kharif 2025](https://pau.edu/content/ccil/pf/pp_kharif.pdf). PAU documents nursery sowing from May 20 to June 20, transplanting from June 20 to July 10, and rice variety durations of 93–117 days after transplant. The broad weather window is therefore May 20 through November 4 inclusive (169 days), using the earliest nursery date and the latest transplant date plus the longest documented duration.

This is explicitly a **normal-calendar proxy**. APY does not contain actual sowing/transplant dates, rice variety, direct-seeding status, or growth stages. The PAU 2025 guidance is applied retrospectively to APY year-start calendar years 2013–2024; it is not evidence of the actual dates followed in each historical year.

IMD’s [Dynamic Crop Weather Calendar user manual](https://mausam.imd.gov.in/imd_latest/contents/agromet/Calendar/UserManualDynamicCropWeatherCalender.pdf) and [GKMS standard operating procedure](https://mausam.imd.gov.in/imd_latest/contents/pdf/gkms_sop.pdf) describe crop-weather information as region-, crop-, season-, and stage-specific and direct calendar preparation toward State Agriculture Departments, KVKs, and SAUs. Tamil Nadu Agricultural University’s [regional rice calendar](https://agritech.tnau.ac.in/agriculture/agri_seasonandvarieties_rice.html) lists locally named seasons and district-zone windows that do not map defensibly to APY’s broad Kharif/Rabi/Summer labels. No weather calendar is therefore inferred for Tamil Nadu or other unsupported crop-state-season combinations. Their APY ranking remains available and their weather profile reports why it is unavailable.

The project assets did not contain a district-level IMD Dynamic Crop Weather Calendar dataset or a verified APY-season crosswalk. The official IMD manual/SOP were used as guidance for calendar eligibility and provenance, not as a substitute for district-specific sowing dates. PAU’s statewide Rice/Kharif guidance is the only current sourced mapping.

## Reproducible weather preprocessing

Run from the project root:

```powershell
application\backend\.venv\Scripts\python.exe phase3b_weather_agriculture\scripts\build_seasonal_weather_features.py
```

The script `phase3b_weather_agriculture/scripts/build_seasonal_weather_features.py` reads the versioned calendar, existing district-grid reference, and daily NASA POWER JSON files, then writes only to the isolated Phase 3B output `phase3b_weather_agriculture/data/seasonal_weather_features.csv`. It discovers years from available variable folders rather than hardcoding a fixed end year. Optional CLI arguments allow alternate raw-data, grid-reference, calendar, and output paths.

For each mapped district and calendar year it resolves the nearest-grid coordinate to a NASA tile, reads the three daily variables, and checks every expected date in the calendar window. A day counts as complete only when precipitation, maximum temperature, and minimum temperature are all finite and valid; precipitation must also be non-negative. Fill values and invalid values are never imputed. If any expected day is missing or invalid, the year’s seasonal aggregates remain null. No partial window is presented as a complete season.

The derived CSV contains 240 district-year rows: 20 mapped Punjab districts × 12 years (2013–2024). All 240 windows have all 169 expected days for all three variables. Twenty of the 23 Punjab districts with valid APY Rice-Kharif evidence have grid mappings; Ferozepur, Malerkotla, and S.A.S Nagar are unmatched. The 20 mapped districts use 14 unique grid cells, so some locations share a grid cell. Recorded district-to-grid distances range from approximately 16.52 to 31.61 km. The API exposes coordinates, mapping distance, coordinate source, source confidence, long-distance flag, and the count of districts sharing that grid cell.

## Weather feature definitions

For each complete district-window-year, the output contains:

- Seasonal total precipitation: sum of valid daily precipitation (mm).
- Mean daily precipitation: arithmetic mean of the daily values (mm/day).
- Maximum daily precipitation: maximum daily value (mm/day).
- Daily rainfall variability: sample standard deviation across daily precipitation values (mm/day).
- Temperature summaries: mean of daily maximum and mean of daily minimum temperature (°C).
- Within-season rainfall distribution: monthly precipitation totals and each month’s share of the window total. Shares are null when the window total is zero.

For a selected district, the API summarizes only complete weather windows whose calendar year matches a valid APY observation year for the selected crop and season. It reports the number of APY-matched years, complete weather years, and complete daily counts. Across matched complete years it reports medians for seasonal totals, daily means, daily variability, and temperature means; the maximum daily precipitation is the maximum across those years. It reports sample standard deviation and coefficient of variation of annual seasonal precipitation when at least two complete years exist. Monthly totals and shares are summarized by month across complete matched years.

Rainy-day, dry-spell, and extreme-temperature counts are null. The current APY records do not specify rice variety or crop stage, and the implementation does not have a sourced threshold applicable to those unspecified conditions. No threshold is invented.

## Historical APY ranking methodology

The request accepts crop, one of the supported APY seasons, and an optional state. It has no user-selected year. APY evidence is filtered through the existing quality service. For each state-district candidate, the response includes:

- Historical median and mean yield over all valid APY observations.
- Recent five-calendar-year median yield, ending at the latest available valid APY year for the selected crop/season/state scope (currently through 2024 in the source data).
- Sample standard deviation and coefficient of variation across all valid observations; CV is standard deviation divided by the all-history mean.
- Valid observation count, distinct observation years, actual observed years, latest observed year, and recent-window coverage.
- Evidence category based only on the count of distinct valid observation years in the recent window: insufficient = 0; limited = 1; moderate = 2–3; strong = 4–5. This is an observation-coverage label, not a yield score or agronomic confidence claim.

District ranks use descending recent five-year median yield only. Ties resolve by descending historical median, then case-insensitive state and district names. Missing years are not filled, interpolated, or treated as zero. Candidates without recent observations remain in the response as unranked with an explanation. If fewer than two candidates have recent observations, the service does not assign comparative ranks and explains the insufficient comparison set.

Weather availability never determines APY ranking position. Weather metrics, weather variability, evidence quality, and agricultural performance remain separate fields and views.

## Current data example

For Rice / Kharif / Punjab, the API returns 23 valid APY district candidates, all rankable from recent data. The first five by the stated ranking basis are:

| Rank | District | Recent five-year median (kg/ha) | Historical median (kg/ha) | Valid APY years |
|---:|---|---:|---:|---:|
| 1 | Malerkotla | 5,291 | 5,291 | 4 |
| 2 | Barnala | 5,221 | 4,827.5 | 12 |
| 3 | Sangrur | 5,157 | 4,871.5 | 12 |
| 4 | Moga | 4,877 | 4,730 | 12 |
| 5 | Ludhiana | 4,816 | 4,760 | 12 |

Malerkotla remains ranked because it has recent APY evidence; its weather profile is unavailable because the existing district-grid reference has no supported mapping. This illustrates why historical agricultural performance and weather coverage are shown separately.

## Application integration

The additive interface appears on the existing Weather Intelligence page. A user selects crop and season and may filter by state; no year is requested. Results display the APY performance ranking, historical yield statistics, observation coverage, evidence category, and a separate district weather profile selector. Unsupported calendars, unmatched geography, unavailable processed features, and incomplete weather windows each produce explicit unavailable states without removing APY evidence.

The API exposes `GET /api/v1/weather-agriculture/options` and `POST /api/v1/weather-agriculture/regions` with typed request/response schemas. Responses include data periods, source files, hashes, weather feature provenance, calendar source/version, grid metadata, warnings, and limitations. The new REST API uses a shared `WeatherAgricultureService` over existing APY and weather services. AI Assistant capability was not expanded. Its existing weather-source text was corrected from the inconsistent IMD attribution to NASA POWER / MERRA2; the established historical weather endpoints were otherwise left unchanged.

## Limitations and interpretation

- The available daily archive covers 2013–2024, which is a short historical period for climate normals and weather-variability estimates.
- Only Punjab Rice Kharif has a calendar mapping in version 1.0.0. No broad-season APY label is treated as an actual crop calendar.
- A 2025 statewide PAU normal calendar is used as a retrospective proxy. It does not reconstruct year-specific farming dates, varieties, management, or crop stages.
- Nearest-grid MERRA2 estimates are not district weather stations. The distance, source mapping confidence, shared cells, and flagged mappings constrain local interpretation.
- Only complete windows receive weather aggregates. Incomplete windows stay null and are not summarized as complete seasons.
- APY observation-year to proxy-calendar-year matching does not prove temporal exposure of the crop to the weather window.
- Historical yield and weather summaries are descriptive. They do not establish weather causation, crop damage, future yield, future suitability, profitability, or guaranteed performance.
- No weather-aware yield model was introduced or evaluated in this phase. The production/manual yield model and future-yield experiments remain unchanged.

Improvements would require a longer daily weather archive, closer or station-based observations, crop/variety and year-specific sowing/transplant/harvest dates, crop-stage data, and sourced district-specific calendars with an explicit crosswalk to APY geography and season definitions. Impact claims would also require suitable crop-loss or damage labels.

## Validation performed

The final combined backend regression run covered `tests/test_weather_agriculture.py`, `tests/test_weather_agriculture_preprocessing.py`, `tests/test_apy_data.py`, `tests/test_weather_data.py`, `tests/test_weather_integration.py`, and `tests/test_assistant.py`: **61 passed, 1 warning** (Starlette/httpx deprecation). Pytest used a workspace-local `tmp_path` fixture because the default Windows temporary directory was denied by the environment.

Frontend `weather-agriculture-explorer.test.tsx` and `api.test.ts`: **14 passed** across 2 files. `pnpm typecheck` passed. Prettier passed for all modified frontend files. ESLint completed with 0 errors and 2 existing ARIA warnings in unrelated crop selectors. The frontend declares Node `>=22.12 <23`; the available runtime was Node 24.19.0, so Vitest was run with the worker-thread runner workaround.

Targeted mypy with imported legacy modules silenced passed for the five changed API/service modules. A full backend mypy run still reports six pre-existing errors in `models/explainability.py`, `models/model_registry.py`, and untouched logic in `assistant/tools.py`. The Phase 3B files pass strict Ruff; full Ruff continues to report 75 pre-existing long-line/unused-import findings in legacy assistant files. No unrelated lint or type issues were changed as part of this implementation.
