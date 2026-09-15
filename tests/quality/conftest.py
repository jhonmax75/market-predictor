from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from market_predictor.quality import FEATURE_COLUMNS


def make_candles(
    n: int = 100,
    *,
    asset_id: str = "BTCUSDT",
    start: str = "2026-01-01 00:00:00+00:00",
) -> pd.DataFrame:
    timestamps = pd.date_range(start=start, periods=n, freq="5min", tz="UTC")
    close = 100.0 + np.arange(n, dtype=float)
    return pd.DataFrame(
        {
            "asset_id": pd.Series([asset_id] * n, dtype="string"),
            "candle_open_ts": timestamps,
            "candle_close_ts": timestamps + pd.Timedelta(minutes=5),
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(n, 1000.0),
        }
    )


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    values = {
        "ret_5m": 0.01,
        "ret_15m": 0.02,
        "ret_1h": 0.05,
        "ret_3h": 0.10,
        "vol_1h": 0.01,
        "vol_6h": 0.02,
        "range_5m": 0.02,
        "range_1h": 0.05,
        "volume_rel_1h": 1.0,
        "volume_trend": 1.0,
    }
    for column in FEATURE_COLUMNS:
        result[column] = values[column]
    return result


def add_target(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["decision_ts"] = result["candle_close_ts"]
    result["target_ts"] = result["decision_ts"] + pd.Timedelta(hours=1)
    result["future_return_1h"] = 0.01
    result["target_direction"] = np.int8(1)
    return result


@pytest.fixture
def valid_candles() -> pd.DataFrame:
    return make_candles()


@pytest.fixture
def valid_dataset() -> pd.DataFrame:
    return add_target(add_features(make_candles()))


@pytest.fixture
def duplicate_primary_key(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([valid_dataset, valid_dataset.iloc[[10]]], ignore_index=True)


@pytest.fixture
def duplicate_candle(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[20, "candle_open_ts"] = result.loc[19, "candle_open_ts"]
    return result


@pytest.fixture
def naive_timestamp(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result["decision_ts"] = result["decision_ts"].dt.tz_localize(None)
    return result


@pytest.fixture
def temporal_gap(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[30:, "candle_open_ts"] += pd.Timedelta(minutes=5)
    return result


@pytest.fixture
def invalid_ohlc(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[20, "high"] = result.loc[20, "low"] - 1
    return result


@pytest.fixture
def negative_price(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[20, "close"] = -10
    return result


@pytest.fixture
def negative_volume(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[20, "volume"] = -1
    return result


@pytest.fixture
def zero_volume(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[20, "volume"] = 0
    return result


@pytest.fixture
def nan_ohlcv(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[20, "close"] = np.nan
    return result


@pytest.fixture
def infinite_feature(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[20, "ret_1h"] = np.inf
    return result


@pytest.fixture
def missing_target(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[70:, "target_ts"] = pd.NaT
    return result


@pytest.fixture
def inconsistent_target(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[20, "future_return_1h"] = 0.10
    result.loc[20, "target_direction"] = np.int8(0)
    return result


@pytest.fixture
def degenerate_target(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result["target_direction"] = np.int8(1)
    return result


@pytest.fixture
def extreme_return(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[20, "ret_5m"] = 0.50
    return result


@pytest.fixture
def extreme_volume(valid_dataset: pd.DataFrame) -> pd.DataFrame:
    result = valid_dataset.copy()
    result.loc[20, "volume"] = 1_000_000_000
    return result
