#!/usr/bin/env python3
from __future__ import annotations

import argparse

from qs.data.ingest_prices import ingest_prices
from qs.data.ingest_fundamentals import ingest_fundamentals


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--tickers', nargs='*', default=None)
    p.add_argument('--start', type=str, default=None)
    args = p.parse_args()

    n_px = ingest_prices(args.tickers, args.start)
    n_fd = 0
    if args.tickers:
        n_fd = ingest_fundamentals(args.tickers)
    print(f"prices rows: {n_px}, fundamentals rows: {n_fd}")


if __name__ == "__main__":
    main()