#!/usr/bin/env python3
from __future__ import annotations

from qs.db import init_db


def main() -> None:
    init_db()
    print("DB initialized")


if __name__ == "__main__":
    main()