#!/usr/bin/env python3
from __future__ import annotations

from qs.backtest import backtest_signal


def main() -> None:
    stats = backtest_signal(signal_name="xgb_alpha")
    print(stats)


if __name__ == "__main__":
    main()