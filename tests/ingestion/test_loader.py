from __future__ import annotations

import pandas as pd

from market_predictor.ingestion.loader import responses_to_dataframe


def test_loader_maps_bybit_rows_to_canonical_columns():
    response = {
        "retCode": 0,
        "retMsg": "OK",
        "result": {
            "list": [
                [
                    "1757969400000",
                    "100.0",
                    "101.0",
                    "99.0",
                    "100.5",
                    "12.5",
                    "1256.25",
                ]
            ]
        },
    }

    dataframe = responses_to_dataframe([response])

    assert list(dataframe.columns) == [
        "timestamp_open",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover",
    ]

    assert len(dataframe) == 1
    assert str(dataframe["timestamp_open"].dt.tz) == "UTC"
    assert dataframe.iloc[0]["open"] == 100.0


def test_loader_does_not_deduplicate():
    row = [
        "1757969400000",
        "100.0",
        "101.0",
        "99.0",
        "100.5",
        "12.5",
        "1256.25",
    ]

    response = {
        "retCode": 0,
        "result": {
            "list": [row, row],
        },
    }

    dataframe = responses_to_dataframe([response])

    assert len(dataframe) == 2


def test_loader_does_not_fill_missing_rows():
    response = {
        "retCode": 0,
        "result": {
            "list": [
                [
                    "1757969400000",
                    "100.0",
                    "101.0",
                    "99.0",
                    "100.5",
                    "12.5",
                    "1256.25",
                ],
                [
                    "1757970000000",
                    "101.0",
                    "102.0",
                    "100.0",
                    "101.5",
                    "13.5",
                    "1360.25",
                ],
            ]
        },
    }

    dataframe = responses_to_dataframe([response])

    assert len(dataframe) == 2

    timestamps = dataframe["timestamp_open"]

    assert timestamps.iloc[1] - timestamps.iloc[0] == pd.Timedelta(minutes=10)

    missing_candle = timestamps.iloc[0] + pd.Timedelta(minutes=5)
    assert missing_candle not in set(timestamps)
