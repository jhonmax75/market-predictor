from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from market_predictor.features.technical import FEATURE_COLUMNS, build_features


def _make_ohlcv(rows: int = 80) -> pd.DataFrame:
    timestamps = pd.date_range("2026-09-15 00:00:00", periods=rows, freq="5min", tz="UTC")
    close = pd.Series(np.linspace(100.0, 179.0, rows), dtype=float)
    return pd.DataFrame(
        {
            "asset_id": "BTCUSDT",
            "candle_open_ts": timestamps,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.arange(1.0, rows + 1.0),
        }
    )


def test_build_features_returns_exact_schema_and_row_count():
    dataframe = _make_ohlcv()

    features = build_features(dataframe)

    assert list(features.columns) == FEATURE_COLUMNS
    assert len(features) == len(dataframe)
    assert all(pd.api.types.is_numeric_dtype(features[column]) for column in FEATURE_COLUMNS)


def test_build_features_uses_frozen_formulas():
    dataframe = _make_ohlcv()
    features = build_features(dataframe)

    assert features.loc[1, "ret_5m"] == pytest.approx(np.log(101.0 / 100.0))
    assert features.loc[3, "ret_15m"] == pytest.approx(np.log(103.0 / 100.0))
    assert features.loc[12, "ret_1h"] == pytest.approx(np.log(112.0 / 100.0))
    assert features.loc[36, "ret_3h"] == pytest.approx(np.log(136.0 / 100.0))
    assert features.loc[0, "range_5m"] == pytest.approx(2.0 / 100.0)
    assert features.loc[12, "volume_rel_1h"] == pytest.approx(13.0 / np.mean(np.arange(1.0, 13.0)))
    assert features.loc[11, "volume_trend"] > 0


def test_features_keep_nan_until_history_is_available():
    features = build_features(_make_ohlcv())

    assert features["ret_5m"].iloc[0] != features["ret_5m"].iloc[0]
    assert features["ret_15m"].iloc[2] != features["ret_15m"].iloc[2]
    assert features["ret_1h"].iloc[11] != features["ret_1h"].iloc[11]
    assert features["ret_3h"].iloc[35] != features["ret_3h"].iloc[35]
    assert features["vol_1h"].iloc[11] != features["vol_1h"].iloc[11]
    assert features["vol_6h"].iloc[71] != features["vol_6h"].iloc[71]
    assert features["range_1h"].iloc[10] != features["range_1h"].iloc[10]
    assert features["volume_rel_1h"].iloc[11] != features["volume_rel_1h"].iloc[11]
    assert features["volume_trend"].iloc[10] != features["volume_trend"].iloc[10]


def test_build_features_does_not_modify_input():
    dataframe = _make_ohlcv()
    original = dataframe.copy(deep=True)

    build_features(dataframe)

    pdt.assert_frame_equal(dataframe, original)


def test_build_features_rejects_missing_canonical_columns():
    dataframe = _make_ohlcv().drop(columns=["volume"])

    with pytest.raises(ValueError, match="volume"):
        build_features(dataframe)


def test_build_features_preserves_small_input_shape():
    dataframe = _make_ohlcv(rows=3)

    features = build_features(dataframe)

    assert features.shape == (3, 10)
    assert features["range_5m"].notna().all()
    assert features["ret_3h"].isna().all()
