from __future__ import annotations

import pandas as pd

from market_predictor.ingestion.normalize import expected_step_interval, normalize_ohlcv


def test_normalize_ohlcv_creates_canonical_schema():
    raw = pd.DataFrame(
        {
            "timestamp_open": [
                pd.Timestamp("2026-09-15 13:00:00", tz="UTC"),
                pd.Timestamp("2026-09-15 13:05:00", tz="UTC"),
            ],
            "open": [100.0, 101.0],
            "high": [101.5, 102.0],
            "low": [99.5, 100.5],
            "close": [101.0, 101.5],
            "volume": [12.5, 13.5],
        }
    )

    normalized = normalize_ohlcv(raw)

    assert list(normalized.columns) == [
        "asset_id",
        "candle_open_ts",
        "candle_close_ts",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert normalized["asset_id"].tolist() == ["BTCUSDT", "BTCUSDT"]
    assert str(normalized["candle_open_ts"].dt.tz) == "UTC"
    assert (normalized["candle_close_ts"] - normalized["candle_open_ts"]).eq(pd.Timedelta(minutes=5)).all()
    assert normalized["candle_open_ts"].is_monotonic_increasing

    deltas = expected_step_interval(normalized)
    assert deltas.dropna().tolist() == [5.0]


def test_normalize_ohlcv_materializes_close_from_open_only():
    opening = pd.to_datetime(["2026-09-15 10:00:00"], utc=True)
    raw = pd.DataFrame(
        {
            "timestamp_open": opening,
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [10.0],
        }
    )

    normalized = normalize_ohlcv(raw)

    assert normalized.loc[0, "candle_close_ts"] == pd.Timestamp(
        "2026-09-15 10:05:00",
        tz="UTC",
    )


def test_normalize_ohlcv_orders_reverse_source_rows_ascending():
    raw = pd.DataFrame(
        {
            "timestamp_open": [
                pd.Timestamp("2026-09-15 13:05:00", tz="UTC"),
                pd.Timestamp("2026-09-15 13:00:00", tz="UTC"),
            ],
            "open": [101.0, 100.0],
            "high": [102.0, 101.0],
            "low": [100.5, 99.5],
            "close": [101.5, 101.0],
            "volume": [13.5, 12.5],
        }
    )

    normalized = normalize_ohlcv(raw)

    assert normalized["candle_open_ts"].is_monotonic_increasing
    assert normalized["open"].tolist() == [100.0, 101.0]


def test_normalize_ohlcv_preserves_duplicates_and_gaps():
    raw = pd.DataFrame(
        {
            "timestamp_open": [
                pd.Timestamp("2026-09-15 13:00:00", tz="UTC"),
                pd.Timestamp("2026-09-15 13:00:00", tz="UTC"),
                pd.Timestamp("2026-09-15 13:15:00", tz="UTC"),
            ],
            "open": [100.0, 100.0, 101.0],
            "high": [101.0, 101.0, 102.0],
            "low": [99.0, 99.0, 100.0],
            "close": [100.5, 100.5, 101.5],
            "volume": [10.0, 10.0, 11.0],
        }
    )

    normalized = normalize_ohlcv(raw)

    assert len(normalized) == 3
    assert normalized["candle_open_ts"].is_monotonic_increasing
    assert normalized["asset_id"].eq("BTCUSDT").all()


def test_normalize_ohlcv_rejects_missing_columns():
    raw = pd.DataFrame({"timestamp_open": [pd.Timestamp("2026-09-15 13:00:00", tz="UTC")]})

    try:
        normalize_ohlcv(raw)
        assert False, "Expected ValueError for missing OHLCV columns"
    except ValueError:
        pass
