from __future__ import annotations

import pandas as pd
import pandas.testing as pdt

from market_predictor.dqc.validator import run_dqc


def _make_valid_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asset_id": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "candle_open_ts": pd.to_datetime(
                [
                    "2026-09-15 13:00:00",
                    "2026-09-15 13:05:00",
                    "2026-09-15 13:10:00",
                ],
                utc=True,
            ),
            "open": [100.0, 101.0, 102.0],
            "high": [101.5, 102.5, 103.5],
            "low": [99.5, 100.5, 101.5],
            "close": [101.0, 101.5, 103.0],
            "volume": [12.5, 13.5, 14.5],
        }
    )


def test_dqc_001_valid_dataset_passes():
    dataframe = _make_valid_dataframe()

    report = run_dqc(dataframe)

    assert report.valid is True
    assert report.issues == ()
    assert report.row_count == 3


def test_dqc_002_gap_of_10_minutes_is_detected():
    dataframe = _make_valid_dataframe().iloc[[0, 2]].copy()
    dataframe = dataframe.reset_index(drop=True)

    report = run_dqc(dataframe)

    assert report.valid is False
    assert report.gap_count == 1
    assert "gaps_detected" in report.issues


def test_dqc_003_duplicate_timestamps_are_detected():
    dataframe = _make_valid_dataframe()
    dataframe.loc[2, "candle_open_ts"] = dataframe.loc[1, "candle_open_ts"]

    report = run_dqc(dataframe)

    assert report.valid is False
    assert report.duplicate_count == 2
    assert "duplicate_timestamps" in report.issues


def test_dqc_004_non_monotonic_timestamps_are_detected():
    dataframe = _make_valid_dataframe().iloc[[2, 0, 1]].copy().reset_index(drop=True)

    report = run_dqc(dataframe)

    assert report.valid is False
    assert "timestamps_not_monotonic" in report.issues


def test_dqc_005_ohlc_inconsistency_is_detected():
    dataframe = _make_valid_dataframe()
    dataframe.loc[1, "high"] = 99.0

    report = run_dqc(dataframe)

    assert report.valid is False
    assert report.ohlc_anomaly_count >= 1
    assert "ohlc_relationship_anomaly" in report.issues


def test_dqc_006_negative_volume_is_detected():
    dataframe = _make_valid_dataframe()
    dataframe.loc[1, "volume"] = -1.0

    report = run_dqc(dataframe)

    assert report.valid is False
    assert "ohlc_relationship_anomaly" in report.issues


def test_dqc_007_nan_values_are_detected():
    dataframe = _make_valid_dataframe()
    dataframe.loc[1, "close"] = float("nan")

    report = run_dqc(dataframe)

    assert report.valid is False
    assert report.null_count > 0
    assert "null_values" in report.issues


def test_dqc_008_missing_required_columns_is_detected():
    dataframe = _make_valid_dataframe().drop(columns=["volume"])

    report = run_dqc(dataframe)

    assert report.valid is False
    assert "missing_columns" in report.issues[0]


def test_dqc_009_wrong_asset_id_is_detected():
    dataframe = _make_valid_dataframe()
    dataframe["asset_id"] = "ETHUSDT"

    report = run_dqc(dataframe)

    assert report.valid is False
    assert "unexpected_asset_id" in report.issues


def test_dqc_010_dqc_does_not_modify_canonical_dataframe():
    dataframe = _make_valid_dataframe()
    original = dataframe.copy(deep=True)

    run_dqc(dataframe)

    pdt.assert_frame_equal(dataframe, original)
