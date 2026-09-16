from __future__ import annotations

import pandas as pd
import pytest

from market_predictor.dataset.schema import (
    canonical_ohlcv_schema,
    validate_ohlcv_contract,
)


def test_canonical_schema_has_expected_columns():
    assert canonical_ohlcv_schema() == [
        "asset_id",
        "candle_open_ts",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]


def _make_valid_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asset_id": ["BTCUSDT", "BTCUSDT"],
            "candle_open_ts": pd.to_datetime(
                ["2026-09-15 13:00:00", "2026-09-15 13:05:00"],
                utc=True,
            ),
            "open": [100.0, 101.0],
            "high": [101.5, 102.0],
            "low": [99.5, 100.5],
            "close": [101.0, 101.5],
            "volume": [12.5, 13.5],
        }
    )


def test_validate_contract_accepts_expected_ohlcv_frame():
    dataframe = _make_valid_dataframe()

    validate_ohlcv_contract(dataframe)


def test_validate_ohlcv_contract_requires_utc():
    dataframe = _make_valid_dataframe()
    dataframe["candle_open_ts"] = dataframe["candle_open_ts"].dt.tz_convert("America/Sao_Paulo")

    with pytest.raises(TypeError, match="UTC"):
        validate_ohlcv_contract(dataframe)


def test_validate_contract_rejects_non_numeric_ohlcv():
    dataframe = pd.DataFrame(
        {
            "asset_id": ["BTCUSDT"],
            "candle_open_ts": pd.to_datetime(["2026-09-15 13:00:00"], utc=True),
            "open": ["bad"],
            "high": [100.0],
            "low": [90.0],
            "close": [95.0],
            "volume": [10.0],
        }
    )

    try:
        validate_ohlcv_contract(dataframe)
        assert False, "Expected TypeError for non-numeric OHLCV"
    except TypeError:
        pass
