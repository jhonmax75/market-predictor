from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.testing as pdt

from market_predictor.dataset.builder import build_dataset
from market_predictor.features.technical import FEATURE_COLUMNS, build_features
from market_predictor.ingestion.normalize import normalize_ohlcv
from market_predictor.targets.direction import build_direction_target


def _make_raw_ohlcv(rows: int = 100) -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-09-15 00:00:00",
        periods=rows,
        freq="5min",
        tz="UTC",
    )
    close = 100.0 + np.arange(rows, dtype=float) * 0.25
    return pd.DataFrame(
        {
            "timestamp_open": timestamps,
            "open": close - 0.2,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
            "volume": 20.0 + np.arange(rows, dtype=float),
        }
    )


def _build_from_raw(raw: pd.DataFrame):
    ohlcv = normalize_ohlcv(raw)
    ohlcv.index = ohlcv["candle_open_ts"]
    features = build_features(ohlcv)
    target = build_direction_target(ohlcv)
    dataset = build_dataset(ohlcv, features, target)
    return ohlcv, features, target, dataset


def test_s6_t01_end_to_end_temporal_chain():
    ohlcv, _features, _target, dataset = _build_from_raw(_make_raw_ohlcv())
    row = dataset.iloc[0]
    source = ohlcv.iloc[72]

    assert row["candle_open_ts"] == source["candle_open_ts"]
    assert row["candle_close_ts"] == source["candle_close_ts"]
    assert row["decision_ts"] == source["candle_close_ts"]
    assert row["target_ts"] == row["decision_ts"] + pd.Timedelta(hours=1)


def test_s6_t02_next_candle_does_not_change_current_features():
    raw = _make_raw_ohlcv()
    _ohlcv, original_features, _target, _dataset = _build_from_raw(raw)

    modified = raw.copy(deep=True)
    modified.loc[73, ["high", "low", "close", "volume"]] += [100.0, 100.0, 100.0, 100.0]
    _modified_ohlcv, modified_features, _target, _dataset = _build_from_raw(modified)

    pdt.assert_frame_equal(
        original_features.iloc[[72]][FEATURE_COLUMNS],
        modified_features.iloc[[72]][FEATURE_COLUMNS],
    )


def test_s6_t03_multiple_future_positions_do_not_change_past_features():
    raw = _make_raw_ohlcv()
    _ohlcv, original_features, _target, _dataset = _build_from_raw(raw)

    for future_position in [73, 77, 84, 96]:
        modified = raw.copy(deep=True)
        modified.loc[future_position, ["high", "low", "close", "volume"]] += 100.0
        _modified_ohlcv, modified_features, _target, _dataset = _build_from_raw(modified)

        pdt.assert_frame_equal(
            original_features.iloc[:future_position][FEATURE_COLUMNS],
            modified_features.iloc[:future_position][FEATURE_COLUMNS],
        )


def test_s6_t04_current_candle_can_change_features_at_its_decision():
    raw = _make_raw_ohlcv()
    _ohlcv, original_features, _target, _dataset = _build_from_raw(raw)

    modified = raw.copy(deep=True)
    modified.loc[72, ["high", "low", "close", "volume"]] += 10.0
    _modified_ohlcv, modified_features, _target, _dataset = _build_from_raw(modified)

    assert original_features.iloc[72][FEATURE_COLUMNS].ne(
        modified_features.iloc[72][FEATURE_COLUMNS]
    ).any()


def test_s6_t05_authorized_future_changes_target_at_t_plus_12():
    raw = _make_raw_ohlcv()
    _ohlcv, _features, original_target, _dataset = _build_from_raw(raw)

    modified = raw.copy(deep=True)
    modified.loc[84, "close"] += 100.0
    _modified_ohlcv, _features, modified_target, _dataset = _build_from_raw(modified)

    assert modified_target.iloc[72]["future_return_1h"] != original_target.iloc[72]["future_return_1h"]


def test_s6_t06_future_beyond_horizon_does_not_change_target():
    raw = _make_raw_ohlcv()
    _ohlcv, _features, original_target, _dataset = _build_from_raw(raw)

    modified = raw.copy(deep=True)
    modified.loc[85, "close"] += 100.0
    _modified_ohlcv, _features, modified_target, _dataset = _build_from_raw(modified)

    pdt.assert_series_equal(
        original_target.iloc[72],
        modified_target.iloc[72],
        check_names=False,
    )


def test_s6_t07_target_future_does_not_change_past_features():
    raw = _make_raw_ohlcv()
    _ohlcv, original_features, _target, _dataset = _build_from_raw(raw)

    modified = raw.copy(deep=True)
    modified.loc[84, "close"] += 100.0
    _modified_ohlcv, modified_features, _target, _dataset = _build_from_raw(modified)

    pdt.assert_frame_equal(
        original_features.iloc[[72]][FEATURE_COLUMNS],
        modified_features.iloc[[72]][FEATURE_COLUMNS],
    )
