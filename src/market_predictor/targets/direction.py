from __future__ import annotations

import numpy as np
import pandas as pd

from market_predictor.dataset.schema import CANONICAL_OHLCV_COLUMNS


TARGET_COLUMNS = ["future_return_1h", "target_direction"]
HORIZON_CANDLES = 12
THRESHOLD = 0.0


def _require_canonical_ohlcv(dataframe: pd.DataFrame) -> None:
    missing = [
        column
        for column in CANONICAL_OHLCV_COLUMNS
        if column not in dataframe.columns
    ]
    if missing:
        raise ValueError(f"Missing canonical OHLCV columns: {missing}")


def build_direction_target(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Build the V1 direction target from close(t) and close(t+12)."""
    _require_canonical_ohlcv(dataframe)

    if len(dataframe) <= HORIZON_CANDLES:
        return pd.DataFrame(
            {
                "future_return_1h": pd.Series(dtype="float64"),
                "target_direction": pd.Series(dtype="Int64"),
            },
            index=dataframe.index[:0],
        )

    close = pd.to_numeric(dataframe["close"], errors="coerce")
    current_close = close.iloc[:-HORIZON_CANDLES]
    future_close = close.iloc[HORIZON_CANDLES:]

    current_values = current_close.to_numpy(dtype=float)
    future_values = future_close.to_numpy(dtype=float)
    valid_prices = (
        np.isfinite(current_values)
        & (current_values > 0)
        & np.isfinite(future_values)
        & (future_values > 0)
    )

    future_return = np.full(len(current_values), np.nan, dtype=float)
    future_return[valid_prices] = np.log(
        future_values[valid_prices] / current_values[valid_prices]
    )
    future_return_series = pd.Series(
        future_return[valid_prices],
        index=dataframe.index[:-HORIZON_CANDLES][valid_prices],
        dtype="float64",
    )

    direction_values = pd.Series(
        (future_return[valid_prices] > THRESHOLD).astype("int64"),
        index=dataframe.index[:-HORIZON_CANDLES][valid_prices],
        dtype="Int64",
    )
    valid_indices = dataframe.index[:-HORIZON_CANDLES][valid_prices]

    return pd.DataFrame(
        {
            "future_return_1h": future_return_series,
            "target_direction": direction_values,
        },
        index=valid_indices,
    )
