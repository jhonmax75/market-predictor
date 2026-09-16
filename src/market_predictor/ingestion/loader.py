from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd


BYBIT_COLUMNS = [
    "timestamp_open_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
]

CANONICAL_COLUMNS = [
    "timestamp_open",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
]


class LoaderError(ValueError):
    """Raised when a Bybit response cannot be loaded."""


def _extract_rows(
    responses: Iterable[dict[str, Any]],
) -> list[list[Any]]:
    rows: list[list[Any]] = []

    for response in responses:
        if not isinstance(response, dict):
            raise LoaderError("Each response must be a dictionary")

        result = response.get("result")

        if not isinstance(result, dict):
            raise LoaderError("Missing Bybit result object")

        page_rows = result.get("list")

        if page_rows is None:
            raise LoaderError("Missing Bybit result.list")

        if not isinstance(page_rows, list):
            raise LoaderError("Bybit result.list must be a list")

        for row in page_rows:
            if not isinstance(row, list):
                raise LoaderError("Each kline row must be a list")

            if len(row) != 7:
                raise LoaderError(
                    f"Expected 7 fields, received {len(row)}"
                )

            rows.append(row)

    return rows


def responses_to_dataframe(
    responses: Iterable[dict[str, Any]],
) -> pd.DataFrame:
    """
    Convert raw Bybit kline responses into a canonical DataFrame.

    No imputation, interpolation, correction, deduplication,
    gap filling or outlier treatment is performed here.
    """

    rows = _extract_rows(responses)

    dataframe = pd.DataFrame(
        rows,
        columns=BYBIT_COLUMNS,
    )

    if dataframe.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    dataframe = dataframe.rename(
        columns={
            "timestamp_open_ms": "timestamp_open",
        }
    )

    dataframe["timestamp_open"] = pd.to_datetime(
        pd.to_numeric(
            dataframe["timestamp_open"],
            errors="coerce",
        ),
        unit="ms",
        utc=True,
    )

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover",
    ]:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe = dataframe[
        [
            "timestamp_open",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "turnover",
        ]
    ]

    return dataframe


def build_collection_metadata(
    *,
    source: str,
    category: str,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    responses: list[dict[str, Any]],
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    """Build auditable metadata for one ingestion run."""

    collection_ts = datetime.now(timezone.utc)

    page_count = len(responses)

    raw_row_count = sum(
        len(
            response.get("result", {}).get("list", [])
        )
        for response in responses
    )

    metadata: dict[str, Any] = {
        "source": source,
        "category": category,
        "symbol": symbol,
        "interval": interval,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "start_utc": datetime.fromtimestamp(
            start_ms / 1000,
            tz=timezone.utc,
        ).isoformat(),
        "end_utc": datetime.fromtimestamp(
            end_ms / 1000,
            tz=timezone.utc,
        ).isoformat(),
        "collection_timestamp_utc": collection_ts.isoformat(),
        "page_count": page_count,
        "raw_row_count": raw_row_count,
        "loaded_row_count": len(dataframe),
        "columns": list(dataframe.columns),
        "normalization": {
            "timestamp_unit": "milliseconds",
            "timestamp_timezone": "UTC",
            "deduplicate": False,
            "fill_missing": False,
            "interpolate": False,
            "winsorize": False,
            "scale": False,
        },
    }

    return metadata
