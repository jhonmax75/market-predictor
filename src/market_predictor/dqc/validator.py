from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from market_predictor.dataset.schema import (
    CANONICAL_OHLCV_COLUMNS,
    DEFAULT_ASSET_ID,
    EXPECTED_TIMEFRAME_MINUTES,
)


@dataclass(frozen=True)
class DQCReport:
    """Immutable result of dataset quality inspection."""

    valid: bool
    row_count: int
    duplicate_count: int
    gap_count: int
    invalid_interval_count: int
    null_count: int
    non_finite_count: int
    ohlc_anomaly_count: int
    issues: tuple[str, ...] = field(default_factory=tuple)


def _count_duplicates(dataframe: pd.DataFrame) -> int:
    return int(dataframe["candle_open_ts"].duplicated(keep=False).sum())


def _intervals(dataframe: pd.DataFrame) -> pd.Series:
    return dataframe["candle_open_ts"].diff().dt.total_seconds().div(60)


def _count_gaps(dataframe: pd.DataFrame) -> int:
    intervals = _intervals(dataframe)
    return int((intervals > EXPECTED_TIMEFRAME_MINUTES).sum())


def _count_invalid_intervals(dataframe: pd.DataFrame) -> int:
    intervals = _intervals(dataframe).dropna()
    return int((intervals <= 0).sum())


def _count_nulls(dataframe: pd.DataFrame) -> int:
    columns = list(CANONICAL_OHLCV_COLUMNS)
    return int(dataframe[columns].isna().sum().sum())


def _count_non_finite(dataframe: pd.DataFrame) -> int:
    numeric_columns = ["open", "high", "low", "close", "volume"]

    count = 0
    for column in numeric_columns:
        values = pd.to_numeric(dataframe[column], errors="coerce")
        count += int(np.isinf(values.to_numpy(dtype=float)).sum())

    return count


def _count_ohlc_anomalies(dataframe: pd.DataFrame) -> int:
    invalid = (
        (dataframe["high"] < dataframe["low"])
        | (dataframe["high"] < dataframe["open"])
        | (dataframe["high"] < dataframe["close"])
        | (dataframe["low"] > dataframe["open"])
        | (dataframe["low"] > dataframe["close"])
        | (dataframe["volume"] < 0)
    )

    return int(invalid.sum())


def run_dqc(
    dataframe: pd.DataFrame,
    *,
    asset_id: str = DEFAULT_ASSET_ID,
) -> DQCReport:
    """Inspect canonical OHLCV without modifying it.

    The function is intentionally non-destructive: no sorting,
    deduplication, filling, interpolation, clipping, winsorization,
    or price correction is performed.
    """

    issues: list[str] = []

    required = set(CANONICAL_OHLCV_COLUMNS)
    missing = required.difference(dataframe.columns)

    if missing:
        return DQCReport(
            valid=False,
            row_count=len(dataframe),
            duplicate_count=0,
            gap_count=0,
            invalid_interval_count=0,
            null_count=0,
            non_finite_count=0,
            ohlc_anomaly_count=0,
            issues=(f"missing_columns:{sorted(missing)}",),
        )

    inspected = dataframe

    if not inspected["asset_id"].eq(asset_id).all():
        issues.append("unexpected_asset_id")

    if not inspected["candle_open_ts"].is_monotonic_increasing:
        issues.append("timestamps_not_monotonic")

    duplicate_count = _count_duplicates(inspected)
    if duplicate_count:
        issues.append("duplicate_timestamps")

    gap_count = _count_gaps(inspected)
    if gap_count:
        issues.append("gaps_detected")

    invalid_interval_count = _count_invalid_intervals(inspected)
    if invalid_interval_count:
        issues.append("invalid_intervals")

    null_count = _count_nulls(inspected)
    if null_count:
        issues.append("null_values")

    non_finite_count = _count_non_finite(inspected)
    if non_finite_count:
        issues.append("non_finite_values")

    ohlc_anomaly_count = _count_ohlc_anomalies(inspected)
    if ohlc_anomaly_count:
        issues.append("ohlc_relationship_anomaly")

    return DQCReport(
        valid=not issues,
        row_count=len(inspected),
        duplicate_count=duplicate_count,
        gap_count=gap_count,
        invalid_interval_count=invalid_interval_count,
        null_count=null_count,
        non_finite_count=non_finite_count,
        ohlc_anomaly_count=ohlc_anomaly_count,
        issues=tuple(issues),
    )
