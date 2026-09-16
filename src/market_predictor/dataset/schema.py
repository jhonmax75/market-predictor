from __future__ import annotations

from typing import Sequence

import pandas as pd


DEFAULT_ASSET_ID = "BTCUSDT"
CANONICAL_OHLCV_COLUMNS: list[str] = [
    "asset_id",
    "candle_open_ts",
    "open",
    "high",
    "low",
    "close",
    "volume",
]

EXPECTED_TIMEFRAME_MINUTES = 5


def canonical_ohlcv_schema() -> list[str]:
    """Return the canonical OHLCV schema for Gate 4."""
    return list(CANONICAL_OHLCV_COLUMNS)


def validate_ohlcv_contract(
    dataframe: pd.DataFrame,
    *,
    asset_id: str = DEFAULT_ASSET_ID,
    require_timezone_utc: bool = True,
) -> None:
    """Validate the Gate 4 canonical schema and contract.

    The contract intentionally preserves duplicates and gaps. It does not clean
    or impute values before the DQC layer.
    """

    expected = canonical_ohlcv_schema()
    missing = [column for column in expected if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {missing}")

    if dataframe.empty:
        return

    if not dataframe["asset_id"].eq(asset_id).all():
        raise ValueError(f"asset_id must be {asset_id!r} for all rows")

    if require_timezone_utc:
        dtype = dataframe["candle_open_ts"].dtype

        if not isinstance(dtype, pd.DatetimeTZDtype):
            raise TypeError("candle_open_ts must be timezone-aware and UTC")

        if str(dataframe["candle_open_ts"].dt.tz) != "UTC":
            raise TypeError("candle_open_ts must use UTC")

    numeric_columns = ["open", "high", "low", "close", "volume"]
    for column in numeric_columns:
        if not pd.api.types.is_numeric_dtype(dataframe[column]):
            raise TypeError(f"{column} must be numeric")

    if not dataframe["candle_open_ts"].is_monotonic_increasing:
        raise ValueError("candle_open_ts must be sorted in ascending order")
