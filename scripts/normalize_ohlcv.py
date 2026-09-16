from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from market_predictor.dataset.schema import validate_ohlcv_contract
from market_predictor.ingestion.loader import CANONICAL_COLUMNS
from market_predictor.ingestion.normalize import normalize_ohlcv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize a raw Bybit candle CSV.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw = pd.read_csv(args.input, parse_dates=["timestamp_open"])
    normalized = normalize_ohlcv(raw)
    validate_ohlcv_contract(normalized)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(args.output, index=False)
    print(f"Normalized rows: {len(normalized)}")
    print(f"Columns: {list(normalized.columns)}")
    print(f"First timestamp: {normalized['candle_open_ts'].iloc[0].isoformat()}")
    print(f"Last timestamp: {normalized['candle_open_ts'].iloc[-1].isoformat()}")


if __name__ == "__main__":
    main()
