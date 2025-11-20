from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mlflow_tracking_uri: str = Field(default=os.getenv("MLFLOW_TRACKING_URI", "./mlruns"))
    duckdb_path: str = Field(default=os.getenv("QS_DUCKDB_PATH", "./data/qs.duckdb"))

    default_tickers: str = Field(default=os.getenv("DEFAULT_TICKERS", "AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA,SPY,QQQ,JPM,BAC"))
    default_start: str = Field(default=os.getenv("DEFAULT_START", "2018-01-01"))

    fmp_api_key: Optional[str] = Field(default=os.getenv("FMP_API_KEY"))

    ibkr_paper: bool = Field(default=bool(int(os.getenv("IBKR_PAPER", "1"))))

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    settings = Settings()
    # ensure dirs
    Path(settings.mlflow_tracking_uri).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.duckdb_path).parent.mkdir(parents=True, exist_ok=True)
    return settings