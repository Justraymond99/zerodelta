from __future__ import annotations

import os
from typing import Iterable
import pandas as pd
import requests
from sqlalchemy import text

from ..config import get_settings
from ..db import get_engine


FMP_BASE = "https://financialmodelingprep.com/api/v3"


def _get(url: str, params: dict) -> list[dict]:
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_fmp_key_metrics(symbols: Iterable[str]) -> pd.DataFrame:
    settings = get_settings()
    if not settings.fmp_api_key:
        return pd.DataFrame(columns=['symbol','date','metric','value'])
    frames: list[pd.DataFrame] = []
    for sym in symbols:
        url = f"{FMP_BASE}/key-metrics/{sym}"
        data = _get(url, {"period": "quarter", "apikey": settings.fmp_api_key})
        if not data:
            continue
        df = pd.DataFrame(data)
        if 'date' not in df:
            continue
        df['symbol'] = sym
        # pick a few core metrics as example
        keep = ['roe', 'roa', 'grossMargin', 'netMargin', 'date', 'symbol']
        df = df[[c for c in keep if c in df.columns]]
        long = df.melt(id_vars=['symbol','date'], var_name='metric', value_name='value')
        frames.append(long)
    if not frames:
        return pd.DataFrame(columns=['symbol','date','metric','value'])
    out = pd.concat(frames, ignore_index=True)
    out['date'] = pd.to_datetime(out['date']).dt.date
    return out.dropna()


def write_fundamentals(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    engine = get_engine()
    with engine.begin() as conn:
        symbols = df['symbol'].unique().tolist()
        min_date = df['date'].min()
        max_date = df['date'].max()
        conn.execute(text(
            "DELETE FROM fundamentals WHERE symbol IN (:symbols) AND date BETWEEN :min_date AND :max_date"
        ), dict(symbols=symbols, min_date=min_date, max_date=max_date))
        df.to_sql('fundamentals', con=conn.connection, if_exists='append', index=False)
    return len(df)


def ingest_fundamentals(tickers: list[str]) -> int:
    df = fetch_fmp_key_metrics(tickers)
    return write_fundamentals(df)