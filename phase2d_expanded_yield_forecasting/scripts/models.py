"""Phase 2D — model zoo and shared design-matrix encoder.

One consistent numeric design matrix is built for every supervised model so the
algorithm comparison is fair. Low-cardinality categoricals (Crop, Season, State)
are one-hot encoded from a *fixed* vocabulary; high-cardinality District is a
stable integer code (one-hot would be ~650 columns). No target information enters
the encoder — vocabulary membership is not a yield value.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from features import NUMERIC_FEATURES

LOW_CARD = ["Crop", "Season", "State"]


def build_vocab(fx: pd.DataFrame) -> dict:
    return {
        "districts": sorted(fx["District"].astype(str).unique()),
        **{c: sorted(fx[c].astype(str).unique()) for c in LOW_CARD},
    }


def make_design(fx: pd.DataFrame, vocab: dict) -> np.ndarray:
    num = fx[NUMERIC_FEATURES].astype(float).to_numpy()
    blocks = [num]
    for c in LOW_CARD:
        cats = vocab[c]
        col = fx[c].astype(str).to_numpy()
        onehot = np.column_stack([(col == k).astype(float) for k in cats])
        blocks.append(onehot)
    dmap = {v: i for i, v in enumerate(vocab["districts"])}
    dcode = fx["District"].astype(str).map(dmap).fillna(-1).to_numpy(dtype=float).reshape(-1, 1)
    blocks.append(dcode)
    return np.hstack(blocks)


def _reg(name: str):
    if name == "ridge":
        return ("ridge", StandardScaler(), Ridge(alpha=10.0))
    if name == "random_forest":
        return ("forest", None, RandomForestRegressor(
            n_estimators=120, min_samples_leaf=5, max_features=0.5,
            n_jobs=-1, random_state=0))
    if name == "gradient_boosting":
        return ("plain", None, GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.1, max_depth=3,
            subsample=0.9, random_state=0))
    if name == "hgb":
        return ("hgb", None, HistGradientBoostingRegressor(
            max_iter=300, learning_rate=0.07, min_samples_leaf=20, random_state=0))
    raise KeyError(name)


class Supervised:
    """Wraps an sklearn regressor over the fixed design matrix."""

    def __init__(self, name: str, vocab: dict):
        self.name = name
        self.vocab = vocab
        self.kind, self.scaler_tmpl, self.est = _reg(name)

    def fit(self, fx: pd.DataFrame, y: np.ndarray = None):
        X = make_design(fx, self.vocab)
        target = fx["target_yield"].to_numpy(dtype=float) if y is None else y
        if self.kind in ("forest", "plain") and len(X) > 60000:
            idx = np.random.RandomState(0).choice(len(X), 60000, replace=False)
            X, target = X[idx], target[idx]
        if self.kind == "ridge":
            self.scaler = StandardScaler().fit(X)
            X = self.scaler.transform(X)
        self.est.fit(X, target)
        return self

    def predict(self, fx: pd.DataFrame) -> np.ndarray:
        X = make_design(fx, self.vocab)
        if self.kind == "ridge":
            X = self.scaler.transform(X)
        return self.est.predict(X)
