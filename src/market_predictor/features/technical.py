from __future__ import annotations

import numpy as np
import pandas as pd

from market_predictor.dataset.schema import CANONICAL_OHLCV_COLUMNS


FEATURE_COLUMNS = [
	"ret_5m",
	"ret_15m",
	"ret_1h",
	"ret_3h",
	"vol_1h",
	"vol_6h",
	"range_5m",
	"range_1h",
	"volume_rel_1h",
	"volume_trend",
]


def _require_ohlcv(dataframe: pd.DataFrame) -> None:
	missing = [column for column in CANONICAL_OHLCV_COLUMNS if column not in dataframe.columns]
	if missing:
		raise ValueError(f"Missing canonical OHLCV columns: {missing}")


def _log_returns(close: pd.Series) -> pd.Series:
	return np.log(close / close.shift(1))


def _rolling_slope(values: pd.Series) -> float:
	x = np.arange(len(values), dtype=float)
	y = values.to_numpy(dtype=float)
	return float(np.polyfit(x, y, 1)[0])


def build_features(dataframe: pd.DataFrame) -> pd.DataFrame:
	"""Build the ten causal V1 technical features without changing input data."""
	_require_ohlcv(dataframe)

	close = pd.to_numeric(dataframe["close"], errors="coerce")
	high = pd.to_numeric(dataframe["high"], errors="coerce")
	low = pd.to_numeric(dataframe["low"], errors="coerce")
	volume = pd.to_numeric(dataframe["volume"], errors="coerce")
	returns = _log_returns(close)

	features = pd.DataFrame(index=dataframe.index)
	features["ret_5m"] = returns
	features["ret_15m"] = np.log(close / close.shift(3))
	features["ret_1h"] = np.log(close / close.shift(12))
	features["ret_3h"] = np.log(close / close.shift(36))
	features["vol_1h"] = returns.rolling(window=12, min_periods=12).std(ddof=1)
	features["vol_6h"] = returns.rolling(window=72, min_periods=72).std(ddof=1)
	features["range_5m"] = (high - low) / close
	features["range_1h"] = (
		high.rolling(window=12, min_periods=12).max()
		- low.rolling(window=12, min_periods=12).min()
	) / close
	features["volume_rel_1h"] = volume / volume.shift(1).rolling(window=12, min_periods=12).mean()
	features["volume_trend"] = np.log1p(volume).rolling(
		window=12,
		min_periods=12,
	).apply(_rolling_slope, raw=False)

	return features[FEATURE_COLUMNS]
