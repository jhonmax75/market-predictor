from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from market_predictor.features.technical import FEATURE_COLUMNS
from market_predictor.targets.direction import build_direction_target


def _make_ohlcv(rows: int = 30) -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-09-15 00:00:00",
        periods=rows,
        freq="5min",
        tz="UTC",
    )
    close = np.full(rows, 100.0)
    return pd.DataFrame(
        {
            "asset_id": "BTCUSDT",
            "candle_open_ts": timestamps,
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 10.0,
        }
    )


def test_g7_t01_uses_exactly_t_plus_12():
    dataframe = _make_ohlcv()
    position = 3
    dataframe.loc[position, "close"] = 100.0
    dataframe.loc[position + 11, "close"] = 101.0
    dataframe.loc[position + 12, "close"] = 120.0
    dataframe.loc[position + 13, "close"] = 80.0

    target = build_direction_target(dataframe)

    assert target.loc[position, "future_return_1h"] == pytest.approx(np.log(120.0 / 100.0))
    assert target.loc[position, "target_direction"] == 1


def test_g7_t02_positive_return_has_direction_one():
    dataframe = _make_ohlcv()
    dataframe.loc[0, "close"] = 100.0
    dataframe.loc[12, "close"] = 101.0

    target = build_direction_target(dataframe)

    assert target.loc[0, "future_return_1h"] > 0
    assert target.loc[0, "target_direction"] == 1


def test_g7_t03_negative_return_has_direction_zero():
    dataframe = _make_ohlcv()
    dataframe.loc[0, "close"] = 100.0
    dataframe.loc[12, "close"] = 99.0

    target = build_direction_target(dataframe)

    assert target.loc[0, "future_return_1h"] < 0
    assert target.loc[0, "target_direction"] == 0


def test_g7_t04_zero_return_has_direction_zero():
    dataframe = _make_ohlcv()

    target = build_direction_target(dataframe)

    assert target.loc[0, "future_return_1h"] == 0.0
    assert target.loc[0, "target_direction"] == 0


def test_g7_t05_excludes_last_twelve_decisions():
    dataframe = _make_ohlcv(rows=20)

    target = build_direction_target(dataframe)

    assert len(target) == 8
    assert list(target.index) == list(range(8))
    assert 8 not in target.index


def test_g7_t06_past_does_not_change_target_at_t():
    dataframe = _make_ohlcv()
    position = 15
    original = build_direction_target(dataframe)

    modified = dataframe.copy(deep=True)
    modified.loc[position - 1, "close"] = 500.0
    changed = build_direction_target(modified)

    pdt.assert_series_equal(
        original.loc[position],
        changed.loc[position],
        check_names=False,
    )


def test_g7_t07_close_at_t_can_change_return():
    dataframe = _make_ohlcv()
    position = 5
    original = build_direction_target(dataframe)

    modified = dataframe.copy(deep=True)
    modified.loc[position, "close"] = 50.0
    changed = build_direction_target(modified)

    assert changed.loc[position, "future_return_1h"] != original.loc[position, "future_return_1h"]


def test_g7_t08_close_at_t_plus_12_can_change_return():
    dataframe = _make_ohlcv()
    position = 5
    original = build_direction_target(dataframe)

    modified = dataframe.copy(deep=True)
    modified.loc[position + 12, "close"] = 150.0
    changed = build_direction_target(modified)

    assert changed.loc[position, "future_return_1h"] != original.loc[position, "future_return_1h"]
    assert changed.loc[position, "target_direction"] == 1


def test_g7_t09_t_plus_13_does_not_change_target():
    dataframe = _make_ohlcv()
    position = 5
    original = build_direction_target(dataframe)

    modified = dataframe.copy(deep=True)
    modified.loc[position + 13, "close"] = 500.0
    changed = build_direction_target(modified)

    pdt.assert_series_equal(
        original.loc[position],
        changed.loc[position],
        check_names=False,
    )


def test_g7_t10_target_columns_are_not_features():
    assert "future_return_1h" not in FEATURE_COLUMNS
    assert "target_direction" not in FEATURE_COLUMNS


def test_g7_t11_target_does_not_mutate_input():
    dataframe = _make_ohlcv()
    original = dataframe.copy(deep=True)

    build_direction_target(dataframe)

    pdt.assert_frame_equal(dataframe, original)


def test_g7_t12_target_is_deterministic():
    dataframe = _make_ohlcv()

    first = build_direction_target(dataframe)
    second = build_direction_target(dataframe)

    pdt.assert_frame_equal(first, second)


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, -np.inf, 0.0, -1.0])
def test_g7_t13_invalid_current_close_excludes_decision(invalid_value):
    dataframe = _make_ohlcv()
    position = 5
    dataframe.loc[position, "close"] = invalid_value

    target = build_direction_target(dataframe)

    assert position not in target.index


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, -np.inf, 0.0, -1.0])
def test_g7_t14_invalid_future_close_excludes_decision(invalid_value):
    dataframe = _make_ohlcv()
    position = 5
    dataframe.loc[position + 12, "close"] = invalid_value

    target = build_direction_target(dataframe)

    assert position not in target.index


def test_target_requires_canonical_ohlcv_columns():
    dataframe = _make_ohlcv().drop(columns=["close"])

    with pytest.raises(ValueError, match="close"):
        build_direction_target(dataframe)
