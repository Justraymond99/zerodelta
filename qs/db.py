from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import get_settings


def get_engine() -> Engine:
    settings = get_settings()
    url = f"duckdb:///{settings.duckdb_path}"
    engine = create_engine(url)
    return engine


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prices (
    symbol TEXT,
    date DATE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    adj_close DOUBLE,
    volume BIGINT,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS fundamentals (
    symbol TEXT,
    date DATE,
    metric TEXT,
    value DOUBLE,
    PRIMARY KEY (symbol, date, metric)
);

CREATE TABLE IF NOT EXISTS features (
    symbol TEXT,
    date DATE,
    feature TEXT,
    value DOUBLE,
    PRIMARY KEY (symbol, date, feature)
);

CREATE TABLE IF NOT EXISTS models (
    model_name TEXT,
    run_id TEXT,
    created_at TIMESTAMP DEFAULT now(),
    params TEXT,
    PRIMARY KEY (model_name)
);

CREATE TABLE IF NOT EXISTS signals (
    symbol TEXT,
    date DATE,
    signal_name TEXT,
    score DOUBLE,
    PRIMARY KEY (symbol, date, signal_name)
);

CREATE TABLE IF NOT EXISTS trades (
    symbol TEXT,
    date DATE,
    side TEXT,
    quantity DOUBLE,
    price DOUBLE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    symbol TEXT,
    side TEXT,
    quantity DOUBLE,
    order_type TEXT,
    limit_price DOUBLE,
    stop_price DOUBLE,
    status TEXT,
    filled_quantity DOUBLE DEFAULT 0,
    average_fill_price DOUBLE,
    created_at TIMESTAMP,
    submitted_at TIMESTAMP,
    filled_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    rejected_at TIMESTAMP,
    rejection_reason TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    quantity DOUBLE,
    average_price DOUBLE,
    last_updated TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS execution_quality (
    order_id TEXT PRIMARY KEY,
    symbol TEXT,
    side TEXT,
    quantity DOUBLE,
    expected_price DOUBLE,
    actual_price DOUBLE,
    slippage DOUBLE,
    slippage_bps DOUBLE,
    timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS strategy_performance (
    strategy_name TEXT,
    date DATE,
    total_return DOUBLE,
    sharpe_ratio DOUBLE,
    max_drawdown DOUBLE,
    win_rate DOUBLE,
    PRIMARY KEY (strategy_name, date)
);

CREATE TABLE IF NOT EXISTS data_quality_log (
    id INTEGER PRIMARY KEY,
    symbol TEXT,
    date DATE,
    issue_type TEXT,
    description TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT now()
);
"""


def init_db() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        for stmt in SCHEMA_SQL.strip().split(";\n\n"):
            if stmt.strip():
                conn.execute(text(stmt))