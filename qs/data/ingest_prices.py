from __future__ import annotations

import math
import pandas as pd
import yfinance as yf
from sqlalchemy import text

from ..config import get_settings
from ..db import get_engine


def fetch_prices(tickers: list[str], start: str) -> pd.DataFrame:
    data = yf.download(tickers, start=start, auto_adjust=False, progress=False, group_by='ticker')
    frames = []
    for symbol in tickers:
        try:
            # Handle both single ticker (flat structure) and multiple tickers (grouped structure)
            if len(tickers) == 1:
                df = data.reset_index()
            else:
                df = data[symbol].reset_index()
            df = df.rename(columns={
                'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Adj Close': 'adj_close', 'Volume': 'volume'
            })
        except Exception:
            # symbol missing in this batch
            continue
        df['symbol'] = symbol
        frames.append(df[['symbol','date','open','high','low','close','adj_close','volume']])
    if not frames:
        return pd.DataFrame(columns=['symbol','date','open','high','low','close','adj_close','volume'])
    out = pd.concat(frames, ignore_index=True)
    out['date'] = pd.to_datetime(out['date']).dt.date
    return out.dropna()


def write_prices(df: pd.DataFrame) -> int:
    engine = get_engine()
    if df.empty:
        return 0
    with engine.begin() as conn:
        symbols = df['symbol'].unique().tolist()
        min_date = df['date'].min()
        max_date = df['date'].max()
        # delete per symbol to avoid array param issue
        for sym in symbols:
            conn.execute(text(
                "DELETE FROM prices WHERE symbol = :sym AND date BETWEEN :min_date AND :max_date"
            ), dict(sym=sym, min_date=min_date, max_date=max_date))
        df.to_sql('prices', con=conn.connection, if_exists='append', index=False)
    return len(df)


def ingest_prices(tickers: list[str] | None = None, start: str | None = None, chunk_size: int = 50) -> int:
    settings = get_settings()
    tickers = tickers or [t.strip() for t in settings.default_tickers.split(',') if t.strip()]
    start = start or settings.default_start
    total = 0
    if not tickers:
        return 0
    for i in range(0, len(tickers), chunk_size):
        batch = tickers[i:i+chunk_size]
        df = fetch_prices(batch, start)
        total += write_prices(df)
    return total


def ingest_prices_from_universe(symbols: list[str], start: str | None = None, chunk_size: int = 50) -> int:
    settings = get_settings()
    start = start or settings.default_start
    return ingest_prices(symbols, start, chunk_size)