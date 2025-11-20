from __future__ import annotations

import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sqlalchemy import text

from ..config import get_settings
from ..db import get_engine

try:
    from xgboost import XGBRegressor  # type: ignore
    _HAS_XGB = True
except Exception:
    XGBRegressor = None  # type: ignore
    _HAS_XGB = False

from sklearn.ensemble import RandomForestRegressor


def prepare_training_frame(horizon: int = 1) -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as conn:
        prices = pd.read_sql(text("SELECT symbol, date, adj_close FROM prices ORDER BY symbol, date"), conn)
        feats = pd.read_sql(text("SELECT symbol, date, feature, value FROM features"), conn)
    if prices.empty or feats.empty:
        return pd.DataFrame()
    # target: next-day return
    prices['ret_fwd'] = prices.groupby('symbol')['adj_close'].pct_change(horizon).shift(-horizon)
    wide = feats.pivot_table(index=['symbol','date'], columns='feature', values='value').reset_index()
    frame = wide.merge(prices[['symbol','date','ret_fwd']], on=['symbol','date'], how='left')
    frame = frame.dropna()
    return frame


def train_model(model_name: str = "xgb_alpha", horizon: int = 1) -> str | None:
    settings = get_settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    frame = prepare_training_frame(horizon=horizon)
    if frame.empty:
        return None
    features = [c for c in frame.columns if c not in ['symbol','date','ret_fwd']]

    # sort by date for time series split
    frame = frame.sort_values('date')
    X = frame[features].to_numpy()
    y = frame['ret_fwd'].to_numpy()

    tscv = TimeSeriesSplit(n_splits=5)

    with mlflow.start_run(run_name=model_name) as run:
        oof_preds = np.zeros_like(y)
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            if _HAS_XGB:
                model = XGBRegressor(
                    n_estimators=300,
                    max_depth=4,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_lambda=1.0,
                    random_state=42,
                    n_jobs=-1,
                )
            else:
                model = RandomForestRegressor(
                    n_estimators=300,
                    max_depth=6,
                    random_state=42,
                    n_jobs=-1,
                )
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            oof_preds[test_idx] = preds
        # Compute RMSE without 'squared' kwarg for compatibility
        rmse = float(np.sqrt(mean_squared_error(y, oof_preds)))
        mlflow.log_metric("rmse", rmse)
        # fit on all data
        if _HAS_XGB:
            final_model = XGBRegressor(
                n_estimators=400,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                reg_lambda=1.0,
                random_state=42,
                n_jobs=-1,
            )
        else:
            final_model = RandomForestRegressor(
                n_estimators=400,
                max_depth=8,
                random_state=42,
                n_jobs=-1,
            )
        final_model.fit(X, y)
        mlflow.sklearn.log_model(final_model, artifact_path="model")
        run_id = run.info.run_id

    # store model pointer
    engine = get_engine()
    params = {"features": features, "horizon": horizon, "model": "xgboost" if _HAS_XGB else "random_forest"}
    import json
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM models WHERE model_name = :name"), {"name": model_name})
        conn.execute(text("INSERT INTO models (model_name, run_id, params) VALUES (:name, :run_id, :params)"),
                     {"name": model_name, "run_id": run_id, "params": json.dumps(params)})
    return run_id