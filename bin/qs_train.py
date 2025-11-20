#!/usr/bin/env python3
from __future__ import annotations

from qs.features import compute_features
from qs.ml.train import train_model


def main() -> None:
    compute_features()
    run_id = train_model(model_name="xgb_alpha")
    print(f"trained run_id: {run_id}")


if __name__ == "__main__":
    main()