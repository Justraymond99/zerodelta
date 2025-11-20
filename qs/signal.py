from __future__ import annotations

import mlflow
import numpy as np
import pandas as pd
from sqlalchemy import text

from .config import get_settings
from .db import get_engine


def load_latest_model_run(model_name: str) -> str | None:
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(text("SELECT run_id FROM models WHERE model_name = :name"), {"name": model_name}).fetchone()
    if not row:
        return None
    return row[0]


def generate_signals(model_name: str = "xgb_alpha") -> int:
    settings = get_settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    run_id = load_latest_model_run(model_name)
    if not run_id:
        return 0

    engine = get_engine()
    with engine.begin() as conn:
        feat = pd.read_sql(text("SELECT symbol, date, feature, value FROM features"), conn)
    if feat.empty:
        return 0
    frame = feat.pivot_table(index=['symbol','date'], columns='feature', values='value').reset_index()
    frame = frame.dropna()
    features = [c for c in frame.columns if c not in ['symbol','date']]

    model_uri = f"runs:/{run_id}/model"
    model = mlflow.sklearn.load_model(model_uri)
    scores = model.predict(frame[features])

    out = pd.DataFrame({
        'symbol': frame['symbol'],
        'date': frame['date'],
        'signal_name': model_name,
        'score': scores
    })

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM signals WHERE signal_name = :name"), {"name": model_name})
        out.to_sql('signals', con=conn.connection, if_exists='append', index=False)
    return len(out)