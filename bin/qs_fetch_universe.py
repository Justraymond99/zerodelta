#!/usr/bin/env python3
from __future__ import annotations

import argparse

from qs.universe import load_sp500_symbols, load_csv_symbols, load_crypto_symbols
from qs.data.ingest_prices import ingest_prices_from_universe


def main() -> None:
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--sp500', action='store_true', help='Use S&P 500 universe')
    group.add_argument('--crypto', action='store_true', help='Use crypto universe')
    group.add_argument('--csv', type=str, help='Path to CSV of symbols')
    p.add_argument('--start', type=str, default=None)
    p.add_argument('--chunk-size', type=int, default=50)
    args = p.parse_args()

    if args.sp500:
        symbols = load_sp500_symbols()
    elif args.crypto:
        symbols = load_crypto_symbols()
    else:
        symbols = load_csv_symbols(args.csv)

    print(f"Symbols: {len(symbols)}")
    n = ingest_prices_from_universe(symbols, start=args.start, chunk_size=args.chunk_size)
    print(f"ingested rows: {n}")


if __name__ == "__main__":
    main()