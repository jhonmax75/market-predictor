from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.testing as pdt

from market_predictor.features.technical import FEATURE_COLUMNS, build_features


def _make_ohlcv(rows: int = 100) -> pd.DataFrame:
    timestamps = pd.date_range("2026-09-15 00:00:00", periods=rows, freq="5min", tz="UTC")
    close = pd.Series(100.0 + np.arange(rows) * 0.25, dtype=float)
    return pd.DataFrame(
        {
            "asset_id": "BTCUSDT",
            "candle_open_ts": timestamps,
            "open": close - 0.2,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
            "volume": 20.0 + np.arange(rows),
        }
    )


def test_future_changes_do_not_change_past_features():
    dataframe = _make_ohlcv()
    original_features = build_features(dataframe)

    for future_position in [1, 5, 12, 36, 72]:
        modified = dataframe.copy(deep=True)
        modified.loc[future_position, "close"] += 500.0
        modified.loc[future_position, "high"] += 500.0
        modified.loc[future_position, "low"] += 500.0
        modified.loc[future_position, "volume"] += 500.0

        modified_features = build_features(modified)
        if future_position > 0:
            pdt.assert_frame_equal(
                original_features.iloc[:future_position],
                modified_features.iloc[:future_position],
            )


def test_current_observation_can_change_current_features():
    dataframe = _make_ohlcv()
    modified = dataframe.copy(deep=True)
    position = 72
    modified.loc[position, "close"] += 10.0
    modified.loc[position, "high"] += 10.0
    modified.loc[position, "low"] += 10.0
    modified.loc[position, "volume"] += 10.0

    original_features = build_features(dataframe)
    modified_features = build_features(modified)

    changed = original_features.loc[position, FEATURE_COLUMNS].ne(
        modified_features.loc[position, FEATURE_COLUMNS]
    )
    assert changed.any()
