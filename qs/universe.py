from __future__ import annotations

import csv
from typing import List

import requests


def load_sp500_symbols() -> List[str]:
    # Try Wikipedia with a browser-like User-Agent
    wiki_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}
    try:
        resp = requests.get(wiki_url, timeout=30, headers=headers)
        resp.raise_for_status()
        html = resp.text
        syms: List[str] = []
        for line in html.split("<tr>"):
            if "</tr>" not in line:
                continue
            parts = line.split("</td>")
            if not parts:
                continue
            cell = parts[0]
            if "<td>" in cell:
                ticker = cell.split("<td>")[-1].strip()
                if 0 < len(ticker) <= 6 and ticker.isupper() and ticker.isascii():
                    syms.append(ticker)
        out = sorted(list({s.replace(".", "-") for s in syms if s.isascii()}))
        out = [s for s in out if s and s[0].isalpha()]
        if len(out) >= 400:
            return out
    except Exception:
        pass

    # Fallback 1: datahub CSV
    urls = [
        "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv",
        "https://raw.githubusercontent.com/datasets/s-and-p-500/master/data/constituents.csv",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=30, headers=headers)
            r.raise_for_status()
            text = r.text.splitlines()
            reader = csv.DictReader(text)
            syms = [row.get('Symbol', '').strip().upper() for row in reader if row.get('Symbol')]
            syms = [s.replace('.', '-') for s in syms]
            out = sorted(list({s for s in syms if s}))
            if len(out) >= 400:
                return out
        except Exception:
            continue

    return []


def load_csv_symbols(path: str) -> List[str]:
    symbols: List[str] = []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            for cell in row:
                for sym in cell.split(','):
                    s = sym.strip().upper()
                    if s:
                        symbols.append(s)
    return sorted(list({s for s in symbols}))


def load_crypto_symbols() -> List[str]:
    """
    Returns a list of common cryptocurrency symbols in yfinance format (e.g., BTC-USD, ETH-USD).
    These symbols can be used directly with yfinance to fetch crypto prices.
    """
    # Major cryptocurrencies with USD pairs
    crypto_symbols = [
        "BTC-USD",  # Bitcoin
        "ETH-USD",  # Ethereum
        "BNB-USD",  # Binance Coin
        "SOL-USD",  # Solana
        "XRP-USD",  # Ripple
        "ADA-USD",  # Cardano
        "DOGE-USD",  # Dogecoin
        "DOT-USD",  # Polkadot
        "MATIC-USD",  # Polygon
        "AVAX-USD",  # Avalanche
        "LINK-USD",  # Chainlink
        "UNI-USD",  # Uniswap
        "LTC-USD",  # Litecoin
        "ATOM-USD",  # Cosmos
        "ETC-USD",  # Ethereum Classic
        "XLM-USD",  # Stellar
        "ALGO-USD",  # Algorand
        "VET-USD",  # VeChain
        "ICP-USD",  # Internet Computer
        "FIL-USD",  # Filecoin
        "TRX-USD",  # Tron
        "EOS-USD",  # EOS
        "AAVE-USD",  # Aave
        "GRT-USD",  # The Graph
        "SAND-USD",  # The Sandbox
        "MANA-USD",  # Decentraland
        "AXS-USD",  # Axie Infinity
        "THETA-USD",  # Theta Network
        "FLOW-USD",  # Flow
        "NEAR-USD",  # NEAR Protocol
    ]
    return sorted(crypto_symbols)