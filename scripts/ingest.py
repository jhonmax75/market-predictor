from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from market_predictor.ingestion.client import BybitClient, BybitClientConfig
from market_predictor.ingestion.loader import (
    build_collection_metadata,
    responses_to_dataframe,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest Bybit Spot OHLCV data."
    )

    parser.add_argument(
        "--start",
        required=True,
        help="Start timestamp in ISO-8601 UTC.",
    )

    parser.add_argument(
        "--end",
        required=True,
        help="End timestamp in ISO-8601 UTC.",
    )

    parser.add_argument(
        "--output",
        default="data/raw",
        help="Raw output directory.",
    )

    return parser.parse_args()


def iso_to_ms(value: str) -> int:
    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")

    return int(timestamp.timestamp() * 1000)


def main() -> None:
    args = parse_args()

    start_ms = iso_to_ms(args.start)
    end_ms = iso_to_ms(args.end)

    client_config = BybitClientConfig(
        category="spot",
        symbol="BTCUSDT",
        interval="5",
        limit=1000,
    )

    client = BybitClient(client_config)

    responses = list(
        client.iter_kline_pages(
            start=start_ms,
            end=end_ms,
        )
    )

    dataframe = responses_to_dataframe(responses)

    collection_timestamp = datetime.now(timezone.utc)
    run_id = collection_timestamp.strftime("%Y%m%dT%H%M%SZ")

    output_dir = (
        Path(args.output)
        / "bybit"
        / client_config.symbol
        / "5m"
        / run_id
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    for index, response in enumerate(responses, start=1):
        raw_path = output_dir / f"raw_response_{index:03d}.json"
        raw_path.write_text(
            json.dumps(response, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    candles_path = output_dir / "candles.csv"
    dataframe.to_csv(candles_path, index=False)

    metadata = build_collection_metadata(
        source="bybit",
        category=client_config.category,
        symbol=client_config.symbol,
        interval=client_config.interval,
        start_ms=start_ms,
        end_ms=end_ms,
        responses=responses,
        dataframe=dataframe,
    )

    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Collection completed: {output_dir}")
    print(f"Pages: {len(responses)}")
    print(f"Rows: {len(dataframe)}")
    print(f"Raw responses: {len(responses)}")


if __name__ == "__main__":
    main()
