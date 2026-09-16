from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from market_predictor.features.technical import FEATURE_COLUMNS
from market_predictor.targets.direction import TARGET_COLUMNS
from market_predictor.dataset.builder import build_dataset


DATASET_COLUMNS = [
    "asset_id",
    "decision_ts",
    *FEATURE_COLUMNS,
    *TARGET_COLUMNS,
]


def _make_inputs(rows: int = 4):
    index = pd.date_range(
        "2026-09-15 13:00:00",
        periods=rows,
        freq="5min",
        tz="UTC",
    )
    close = np.arange(100.0, 100.0 + rows)

    ohlcv = pd.DataFrame(
        {
            "asset_id": "BTCUSDT",
            "candle_open_ts": index,
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 10.0,
        },
        index=index,
    )
    features = pd.DataFrame(
        {
            column: np.arange(rows, dtype=float) + position * 100.0
            for position, column in enumerate(FEATURE_COLUMNS)
        },
        index=index,
    )
    target = pd.DataFrame(
        {
            "future_return_1h": np.arange(rows, dtype=float) / 100.0,
            "target_direction": pd.Series([0, 1, 0, 1][:rows], index=index, dtype="Int64"),
        },
        index=index,
    )
    return ohlcv, features, target


def test_g8_t01_output_has_exact_14_column_schema():
    ohlcv, features, target = _make_inputs()

    result = build_dataset(ohlcv, features, target)

    assert list(result.columns) == DATASET_COLUMNS
    assert len(result.columns) == 14


def test_g8_t02_logical_key_exists():
    ohlcv, features, target = _make_inputs()

    result = build_dataset(ohlcv, features, target)

    assert {"asset_id", "decision_ts"}.issubset(result.columns)


def test_g8_t03_logical_key_is_unique():
    ohlcv, features, target = _make_inputs()
    duplicate = ohlcv.iloc[[0]].copy()
    ohlcv = pd.concat([ohlcv, duplicate])
    features = pd.concat([features, features.iloc[[0]]])
    target = pd.concat([target, target.iloc[[0]]])

    with pytest.raises(ValueError, match="duplicate.*(timestamp|key)"):
        build_dataset(ohlcv, features, target)


def test_g8_t04_decision_timestamp_equals_candle_open_timestamp():
    ohlcv, features, target = _make_inputs()

    result = build_dataset(ohlcv, features, target)

    expected = ohlcv.loc[result["decision_ts"], "candle_open_ts"].reset_index(drop=True)
    actual = result["decision_ts"].reset_index(drop=True)

    pdt.assert_series_equal(
        actual,
        expected,
        check_names=False,
    )


def test_g8_t05_features_are_aligned_to_same_t():
    ohlcv, features, target = _make_inputs()
    features.loc[features.index[1], "ret_5m"] = 999.0

    result = build_dataset(ohlcv, features, target)

    assert result.loc[result["decision_ts"] == ohlcv.index[1], "ret_5m"].iloc[0] == 999.0


def test_g8_t06_target_is_aligned_to_same_t():
    ohlcv, features, target = _make_inputs()
    target.loc[target.index[1], "future_return_1h"] = 0.77

    result = build_dataset(ohlcv, features, target)

    assert result.loc[result["decision_ts"] == target.index[1], "future_return_1h"].iloc[0] == 0.77


def test_g8_t07_builder_does_not_shift_target():
    ohlcv, features, target = _make_inputs()
    target["future_return_1h"] = [0.11, 0.22, 0.33, 0.44]

    result = build_dataset(ohlcv, features, target)

    assert result["future_return_1h"].tolist() == [0.11, 0.22, 0.33, 0.44]


def test_g8_t08_builder_does_not_create_future_features():
    ohlcv, features, target = _make_inputs()
    original_features = features.copy(deep=True)

    result = build_dataset(ohlcv, features, target)

    assert list(result.columns[2:12]) == FEATURE_COLUMNS
    pdt.assert_frame_equal(features, original_features)


def test_g8_t09_nan_feature_excludes_decision():
    ohlcv, features, target = _make_inputs()
    invalid_index = features.index[1]
    features.loc[invalid_index, "ret_5m"] = np.nan

    result = build_dataset(ohlcv, features, target)

    assert invalid_index not in set(result["decision_ts"])


def test_g8_t10_nan_target_excludes_decision():
    ohlcv, features, target = _make_inputs()
    invalid_index = target.index[1]
    target.loc[invalid_index, "future_return_1h"] = np.nan

    result = build_dataset(ohlcv, features, target)

    assert invalid_index not in set(result["decision_ts"])


def test_g8_t11_infinite_values_are_excluded():
    ohlcv, features, target = _make_inputs()
    invalid_index = features.index[1]
    features.loc[invalid_index, "ret_5m"] = np.inf
    target.loc[target.index[2], "future_return_1h"] = -np.inf

    result = build_dataset(ohlcv, features, target)

    assert np.isfinite(result.select_dtypes(include=[np.number]).to_numpy()).all()
    assert invalid_index not in set(result["decision_ts"])
    assert target.index[2] not in set(result["decision_ts"])


def test_g8_t12_final_dataset_contains_no_nan():
    ohlcv, features, target = _make_inputs()
    features.loc[features.index[1], "ret_5m"] = np.nan
    target.loc[target.index[2], "future_return_1h"] = np.nan

    result = build_dataset(ohlcv, features, target)

    assert not result.isna().any().any()


def test_g8_t13_duplicate_key_raises_without_deduplication():
    ohlcv, features, target = _make_inputs()
    ohlcv = pd.concat([ohlcv, ohlcv.iloc[[0]]])
    features = pd.concat([features, features.iloc[[0]]])
    target = pd.concat([target, target.iloc[[0]]])

    with pytest.raises(ValueError):
        build_dataset(ohlcv, features, target)


def test_g8_t14_rejects_noncanonical_input_order():
    ohlcv, features, target = _make_inputs()
    order = [2, 0, 3, 1]
    ohlcv = ohlcv.iloc[order]
    features = features.iloc[order]
    target = target.iloc[order]

    with pytest.raises(ValueError, match="order|sorted|monotonic"):
        build_dataset(ohlcv, features, target)


def test_g8_t15_inputs_are_not_mutated():
    ohlcv, features, target = _make_inputs()
    original = [ohlcv.copy(deep=True), features.copy(deep=True), target.copy(deep=True)]

    build_dataset(ohlcv, features, target)

    for actual, expected in zip((ohlcv, features, target), original):
        pdt.assert_frame_equal(actual, expected)


def test_g8_t16_build_is_deterministic():
    ohlcv, features, target = _make_inputs()

    first = build_dataset(ohlcv, features, target)
    second = build_dataset(ohlcv, features, target)

    pdt.assert_frame_equal(first, second)


def test_g8_t17_output_is_valid_intersection():
    ohlcv, features, target = _make_inputs()
    features = features.drop(index=features.index[1])
    target = target.drop(index=target.index[2])

    result = build_dataset(ohlcv, features, target)

    assert list(result["decision_ts"]) == [ohlcv.index[0], ohlcv.index[3]]


def test_g8_t18_missing_required_columns_raise():
    ohlcv, features, target = _make_inputs()
    features = features.drop(columns=["ret_5m"])

    with pytest.raises(ValueError, match="ret_5m"):
        build_dataset(ohlcv, features, target)


def test_g8_t19_conflicting_asset_ids_raise():
    ohlcv, features, target = _make_inputs()
    ohlcv.loc[ohlcv.index[1], "asset_id"] = "ETHUSDT"

    with pytest.raises(ValueError, match="asset"):
        build_dataset(ohlcv, features, target)


def test_g8_t20_incompatible_timestamps_raise():
    ohlcv, features, target = _make_inputs()
    shifted_index = features.index + pd.Timedelta(minutes=5)
    features.index = shifted_index

    with pytest.raises(ValueError, match="timestamp|align|index"):
        build_dataset(ohlcv, features, target)


def test_g8_t21_ohlcv_index_must_match_candle_open_timestamp():
    ohlcv, features, target = _make_inputs()
    ohlcv.index = ohlcv.index + pd.Timedelta(minutes=5)

    with pytest.raises(ValueError, match="index.*candle_open_ts"):
        build_dataset(ohlcv, features, target)


def test_g8_t22_identity_temporal_alignment_uses_target_at_t():
    ohlcv, features, target = _make_inputs()
    t = ohlcv.index[1]
    features.loc[t, "ret_5m"] = 111.0
    target.loc[t, "future_return_1h"] = 222.0
    target.loc[ohlcv.index[2], "future_return_1h"] = 333.0

    result = build_dataset(ohlcv, features, target)
    row = result.loc[result["decision_ts"] == t].iloc[0]

    assert row["ret_5m"] == 111.0
    assert row["future_return_1h"] == 222.0
    assert row["future_return_1h"] != 333.0
