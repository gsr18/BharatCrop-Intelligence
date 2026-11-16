"""Phase 2C - Parts 2-5: leakage-free future-yield forecasting research.

Builds an origin-safe panel from the APY long dataset and evaluates, with
expanding-window rolling-origin validation:
  * Baselines : naive carry-forward (last observed yield), historical group
                median, per-series trend extrapolation.
  * ML models : Ridge, RandomForest, HistGradientBoostingRegressor (pooled panel).

Two forecast horizons are evaluated independently: T+1 and T+2.
A prediction for target year Y at horizon h uses ONLY data from years <= Y-h.

Nothing here is wired into the production API. It reads source data read-only
and writes research artifacts under phase2c_future_yield_forecasting/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
LONG = ROOT / "data" / "processed" / "historical_food_grains_apy_long_2013-14_to_2024-25.csv"
OUT = Path(__file__).resolve().parents[1] / "artifacts"
OUT.mkdir(parents=True, exist_ok=True)

SEASONS = ("Kharif", "Rabi", "Summer")  # exclude 'Total' aggregate season
KEY = ["State", "District", "Crop", "Season"]
CATEGORICAL = ["Crop", "Season", "State", "District"]
NUMERIC = [
    "y_origin", "y_origin_lag1", "y_origin_lag2",
    "hist_median", "hist_mean", "hist_std", "hist_n",
    "lag_dev", "trend_slope", "origin_year", "target_year",
]
MAX_PLAUSIBLE_YIELD = 12000.0  # kg/ha; documented robustness cap (see Part 6)
FIRST_EVAL_YEAR = 2017  # need >=4 prior target-years of history to train


def load_cohort(robust: bool) -> pd.DataFrame:
    df = pd.read_csv(
        LONG,
        usecols=[
            "State", "District", "Crop", "Season", "Crop_Category",
            "Year", "Area", "Production", "Yield",
        ],
    )
    df["YearStart"] = df["Year"].astype(str).str.extract(r"^(\d{4})")[0].astype(float)
    for c in ("Yield", "Area", "Production"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["Crop_Category"] == "Individual Crop Candidate"]
    df = df[df["Season"].isin(SEASONS)]
    df = df[df["Yield"] > 0]
    if robust:
        # Well-formed only: positive area & production, plausible yield.
        df = df[(df["Area"] > 0) & (df["Production"] > 0) & (df["Yield"] <= MAX_PLAUSIBLE_YIELD)]
    return df.dropna(subset=KEY + ["YearStart"]).reset_index(drop=True)


def build_forecast_rows(df: pd.DataFrame, horizons=(1, 2)) -> pd.DataFrame:
    """Create one row per (series, target_year, horizon) with origin-safe features."""
    rows = []
    for _, grp in df.groupby(KEY, sort=False):
        g = grp.sort_values("YearStart")
        ymap = dict(zip(g["YearStart"].astype(int), g["Yield"]))
        years_sorted = sorted(ymap)
        meta = g[["State", "District", "Crop", "Season"]].iloc[0].to_dict()
        for target_year, target_yield in ymap.items():
            for h in horizons:
                origin = target_year - h
                if origin not in ymap:
                    continue  # need a last-known observation at the origin
                hist = [ymap[y] for y in years_sorted if y <= origin]
                if len(hist) < 1:
                    continue
                y_o = ymap[origin]
                y_o1 = ymap.get(origin - 1, np.nan)
                y_o2 = ymap.get(origin - 2, np.nan)
                hmed = float(np.median(hist))
                hmean = float(np.mean(hist))
                hstd = float(np.std(hist)) if len(hist) >= 2 else 0.0
                # Trend fit over years <= origin (>=3 points)
                if len(hist) >= 3:
                    hy = [y for y in years_sorted if y <= origin]
                    slope, _ = np.polyfit(np.asarray(hy, float), np.asarray(hist, float), 1)
                    trend_slope = float(slope)
                    trend_pred = float(slope * target_year + (_intercept(hy, hist)))
                else:
                    trend_slope = 0.0
                    trend_pred = hmean
                rows.append({
                    **meta,
                    "horizon": h,
                    "origin_year": origin,
                    "target_year": target_year,
                    "y_origin": y_o,
                    "y_origin_lag1": y_o1 if not np.isnan(y_o1) else hmed,
                    "y_origin_lag2": y_o2 if not np.isnan(y_o2) else hmed,
                    "hist_median": hmed,
                    "hist_mean": hmean,
                    "hist_std": hstd,
                    "hist_n": len(hist),
                    "lag_dev": y_o - hmean,
                    "trend_slope": trend_slope,
                    "target_yield": float(target_yield),
                    # baselines (origin-only)
                    "b_prev": y_o,
                    "b_median": hmed,
                    "b_trend": trend_pred,
                })
    return pd.DataFrame(rows)


def _intercept(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    return float(np.mean(y) - np.polyfit(x, y, 1)[0] * np.mean(x))


def make_matrix(fx: pd.DataFrame):
    num = fx[NUMERIC].astype(float).values
    cat = fx[CATEGORICAL].copy()
    return num, cat


class RidgeModel:
    def fit(self, fx):
        self.mu = fx["hist_median"].mean()
        self.sd = fx["hist_median"].std() or 1.0
        num = fx[NUMERIC].astype(float).values
        self.sc = StandardScaler().fit(num)
        oh = pd.get_dummies(fx[["Crop", "Season"]], drop_first=True).astype(float).values
        self.X_oh_dim = oh.shape[1]
        X = np.hstack([self.sc.transform(num), oh])
        self.m = Ridge(alpha=10.0).fit(X, fx["target_yield"].values)
        return self

    def predict(self, fx):
        num = fx[NUMERIC].astype(float).values
        oh = pd.get_dummies(fx[["Crop", "Season"]], drop_first=True).astype(float).values
        if oh.shape[1] < self.X_oh_dim:  # align dummy columns defensively
            pad = np.zeros((oh.shape[0], self.X_oh_dim - oh.shape[1]))
            oh = np.hstack([oh, pad])
        X = np.hstack([self.sc.transform(num), oh[:, : self.X_oh_dim]])
        return self.m.predict(X)


class RFModel:
    CODES = [f"{c}__code" for c in CATEGORICAL]

    def fit(self, fx):
        X = fx[NUMERIC + self.CODES].astype(float).values
        self.m = RandomForestRegressor(
            n_estimators=150, min_samples_leaf=5, n_jobs=-1, random_state=0,
        ).fit(X, fx["target_yield"].values)
        return self

    def predict(self, fx):
        X = fx[NUMERIC + self.CODES].astype(float).values
        return self.m.predict(X)


class HGBModel:
    LOW_CARD = ["Crop", "Season", "State"]

    def _matrix(self, fx):
        X = fx[NUMERIC + self.LOW_CARD].copy()
        X["District_code"] = fx["District__code"].astype(float)
        for c in self.LOW_CARD:
            X[c] = X[c].astype("category")
        cat_idx = [
            X.columns.get_loc(c) for c in self.LOW_CARD
        ]
        return X, cat_idx

    def fit(self, fx):
        X, cat_idx = self._matrix(fx)
        self.m = HistGradientBoostingRegressor(
            max_iter=250, learning_rate=0.08, min_samples_leaf=20,
            categorical_features=cat_idx, random_state=0,
        ).fit(X, fx["target_yield"].values)
        return self

    def predict(self, fx):
        X, _ = self._matrix(fx)
        return self.m.predict(X)


MODELS = {"ridge": RidgeModel, "random_forest": RFModel, "hgb": HGBModel}
BASELINES = {"baseline_prev": "b_prev", "baseline_median": "b_median", "baseline_trend": "b_trend"}


def metrics(actual, pred):
    actual = np.asarray(actual, float)
    pred = np.asarray(pred, float)
    err = pred - actual
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    bias = float(np.mean(err))
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return {"mae": mae, "rmse": rmse, "bias": bias, "r2": r2, "n": int(len(actual))}


def rolling_origin_eval(df: pd.DataFrame, model_name: str, fitter):
    """Expanding window by target year. Train on target_year < Y, test on == Y."""
    all_fx = build_forecast_rows(df)
    for c in CATEGORICAL:
        vocab = sorted(all_fx[c].astype(str).unique())
        lookup = {v: i for i, v in enumerate(vocab)}
        all_fx[f"{c}__code"] = all_fx[c].astype(str).map(lookup).astype(float)
    preds, actuals, keys = [], [], []
    for h in (1, 2):
        sub = all_fx[all_fx["horizon"] == h].reset_index(drop=True)
        for y in range(FIRST_EVAL_YEAR, int(sub["target_year"].max()) + 1):
            train = sub[sub["target_year"] < y]
            test = sub[sub["target_year"] == y]
            if len(train) < 200 or len(test) == 0:
                continue
            mdl = fitter().fit(train)
            p = mdl.predict(test)
            preds.extend(list(p))
            actuals.extend(list(test["target_yield"].values))
            keys.append(
                pd.DataFrame({
                    "horizon": h, "target_year": y,
                    "State": test["State"].values, "District": test["District"].values,
                    "Crop": test["Crop"].values, "Season": test["Season"].values,
                    "actual": test["target_yield"].values, "pred": p,
                    "b_prev": test["b_prev"].values, "b_median": test["b_median"].values,
                    "b_trend": test["b_trend"].values,
                })
            )
    detail = pd.concat(keys, ignore_index=True)
    detail.to_csv(OUT / f"predictions_{model_name}.csv", index=False)
    return detail


def evaluate_cohort(robust: bool):
    tag = "wellformed" if robust else "full"
    df = load_cohort(robust)
    results: dict = {"cohort": tag, "n_obs_yield_gt0": int(len(df))}
    combined_detail = []
    for name, fitter in MODELS.items():
        detail = rolling_origin_eval(df, f"{tag}_{name}", fitter)
        combined_detail.append(detail)

    # Stack baselines from the ml detail (same rows for a given model/cohort)
    # Baselines are model-independent; use one detail's rows.
    det = combined_detail[0]
    overall = {"horizon_all": {}, "horizon_1": {}, "horizon_2": {}}
    scores = {}

    def score_block(sub, label):
        blk = {}
        for bl, col in BASELINES.items():
            blk[bl] = metrics(sub["actual"], sub[col])
        for name in MODELS:
            p = sub[f"{tag}_{name}_pred"]
            blk[name] = metrics(sub["actual"], p)
        overall[label] = blk

    # Merge model predictions onto shared row key (horizon,target_year,geo...)
    base = det[["horizon", "target_year", "State", "District", "Crop", "Season",
                "actual", "b_prev", "b_median", "b_trend"]].copy()
    for d in combined_detail[1:]:
        pass  # predictions already merged below
    merged = base.copy()
    for name in MODELS:
        dd = pd.read_csv(OUT / f"predictions_{tag}_{name}.csv")
        merged[f"{tag}_{name}_pred"] = dd["pred"].values
    score_block(merged, "horizon_all")
    score_block(merged[merged["horizon"] == 1], "horizon_1")
    score_block(merged[merged["horizon"] == 2], "horizon_2")

    # by crop (best-effort, top coverage)
    by_crop = {}
    for crop, sub in merged.groupby("Crop"):
        if len(sub) < 200:
            continue
        by_crop[crop] = {
            "n": int(len(sub)),
            "baseline_median_mae": metrics(sub["actual"], sub["b_median"])["mae"],
            "hgb_mae": metrics(sub["actual"], sub[f"{tag}_hgb_pred"])["mae"],
        }

    merged.to_csv(OUT / f"merged_predictions_{tag}.csv", index=False)
    results["metrics"] = overall
    results["n_evaluated"] = int(len(merged))
    results["n_groups"] = int(merged.groupby(["State", "District", "Crop", "Season"]).ngroups)
    results["by_crop"] = by_crop
    return results


def main():
    summary = {
        "config": {
            "seasons": list(SEASONS),
            "horizons": [1, 2],
            "first_eval_year": FIRST_EVAL_YEAR,
            "max_plausible_yield": MAX_PLAUSIBLE_YIELD,
            "numeric_features": NUMERIC,
            "categorical_features": CATEGORICAL,
        },
        "cohorts": {},
    }
    for robust in (True, False):
        summary["cohorts"]["wellformed" if robust else "full"] = evaluate_cohort(robust)
    (OUT / "forecast_evaluation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary["cohorts"]["wellformed"]["metrics"], indent=2))
    print("n_eval wellformed:", summary["cohorts"]["wellformed"]["n_evaluated"],
          "groups:", summary["cohorts"]["wellformed"]["n_groups"])
    print("n_eval full:", summary["cohorts"]["full"]["n_evaluated"],
          "groups:", summary["cohorts"]["full"]["n_groups"])


if __name__ == "__main__":
    main()
