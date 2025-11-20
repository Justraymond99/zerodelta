#!/usr/bin/env python3
from __future__ import annotations

import sys
import subprocess

def main():
    """Run Alembic migrations."""
    # Forward all arguments to alembic
    result = subprocess.run(["alembic"] + sys.argv[1:])
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()

