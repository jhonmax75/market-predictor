from __future__ import annotations

from typing import Any

import pandas as pd

from market_predictor.dataset.schema import DEFAULT_ASSET_ID, CANONICAL_OHLCV_COLUMNS


def normalize_ohlcv(
    dataframe: pd.DataFrame,
    *,
    asset_id: str = DEFAULT_ASSET_ID,
) -> pd.DataFrame:
    """Build the canonical Gate 4 OHLCV table from a raw Bybit DataFrame.

    The transformation is intentionally minimal and non-destructive:
    - creates asset_id
    - renames and preserves candle-open timestamps as timezone-aware UTC
    - keeps the numeric OHLCV values without any imputation or deduplication
    - does not fill gaps
    - does not modify price levels
    """

    if dataframe.empty:
        normalized = pd.DataFrame(columns=CANONICAL_OHLCV_COLUMNS)
        normalized["asset_id"] = pd.Series(dtype="object")
        normalized["candle_open_ts"] = pd.Series(dtype="datetime64[ns, UTC]")
        for column in ["open", "high", "low", "close", "volume"]:
            normalized[column] = pd.Series(dtype="float64")
        return normalized

    normalized = dataframe.copy()

    if "timestamp_open" in normalized.columns:
        normalized = normalized.rename(columns={"timestamp_open": "candle_open_ts"})

    if "candle_open_ts" not in normalized.columns:
        raise ValueError("Input dataframe must contain 'candle_open_ts' or 'timestamp_open'")

    normalized["candle_open_ts"] = pd.to_datetime(
        normalized["candle_open_ts"],
        utc=True,
        errors="raise",
    )

    for column in ["open", "high", "low", "close", "volume"]:
        if column not in normalized.columns:
            raise ValueError(f"Missing OHLCV column: {column}")
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized["asset_id"] = asset_id
    normalized = normalized[[
        "asset_id",
        "candle_open_ts",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]]
    normalized = normalized.sort_values(
        "candle_open_ts",
        kind="stable",
        ignore_index=True,
    )

    return normalized


def expected_step_interval(dataframe: pd.DataFrame) -> pd.Series:
    """Return the time delta between consecutive candles in minutes."""
    timestamps = dataframe["candle_open_ts"].sort_values()
    return timestamps.diff().dt.total_seconds().div(60)
