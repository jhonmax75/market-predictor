from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from market_predictor.features.technical import FEATURE_COLUMNS
from market_predictor.targets.direction import TARGET_COLUMNS
from market_predictor.dataset.schema import EXPECTED_TIMEFRAME_MINUTES


DATASET_COLUMNS = [
	"asset_id",
	"candle_open_ts",
	"candle_close_ts",
	"decision_ts",
	"target_ts",
	*FEATURE_COLUMNS,
	*TARGET_COLUMNS,
]


def _require_columns(
	dataframe: pd.DataFrame,
	required: list[str],
	name: str,
) -> None:
	missing = [column for column in required if column not in dataframe.columns]
	if missing:
		raise ValueError(f"Missing {name} columns: {missing}")


def _validate_ohlcv(ohlcv: pd.DataFrame) -> None:
	_require_columns(ohlcv, ["asset_id", "candle_open_ts", "candle_close_ts"], "OHLCV")
	expected_index = pd.Index(
		ohlcv["candle_open_ts"].tolist(),
		name=ohlcv["candle_open_ts"].name,
	)
	if not ohlcv.index.equals(expected_index):
		raise ValueError("OHLCV index must match candle_open_ts")

	if ohlcv["asset_id"].nunique(dropna=False) != 1:
		raise ValueError("OHLCV input must contain exactly one asset")

	if ohlcv["candle_open_ts"].duplicated().any():
		raise ValueError("duplicate decision timestamps are not allowed")

	if not ohlcv["candle_open_ts"].is_monotonic_increasing:
		raise ValueError("OHLCV timestamps must be sorted in ascending order")

	if not (
		 ohlcv["candle_close_ts"]
		 == ohlcv["candle_open_ts"] + pd.Timedelta(minutes=EXPECTED_TIMEFRAME_MINUTES)
	).all():
		raise ValueError("candle_close_ts must equal candle_open_ts plus 5 minutes")


def _validate_index(
	dataframe: pd.DataFrame,
	name: str,
	expected_index: pd.Index,
) -> None:
	if not dataframe.index.isin(expected_index).all():
		raise ValueError(f"{name} index is incompatible with OHLCV timestamps")

	if not dataframe.index.is_unique:
		raise ValueError(f"duplicate {name.lower()} timestamps are not allowed")

	if not dataframe.index.is_monotonic_increasing:
		raise ValueError(f"{name} timestamps must be sorted in ascending order")


def _validate_unique_decision_keys(dataframe: pd.DataFrame) -> None:
	if dataframe[["asset_id", "decision_ts"]].duplicated().any():
		raise ValueError("duplicate decision keys are not allowed")


def build_dataset(
	ohlcv: pd.DataFrame,
	features: pd.DataFrame,
	target: pd.DataFrame,
) -> pd.DataFrame:
	"""Compose aligned OHLCV identity, features, and target into V1 data."""
	_validate_ohlcv(ohlcv)
	_require_columns(features, FEATURE_COLUMNS, "feature")
	_require_columns(target, TARGET_COLUMNS, "target")

	expected_index = pd.Index(
		ohlcv["candle_open_ts"].tolist(),
		name=ohlcv["candle_open_ts"].name,
	)
	_validate_index(features, "Feature", expected_index)
	_validate_index(target, "Target", expected_index)

	result = pd.DataFrame(
		{
			"asset_id": ohlcv["asset_id"].copy(),
			"candle_open_ts": ohlcv["candle_open_ts"].copy(),
			"candle_close_ts": ohlcv["candle_close_ts"].copy(),
			"decision_ts": ohlcv["candle_close_ts"].copy(),
			"target_ts": ohlcv["candle_close_ts"].copy() + pd.Timedelta(hours=1),
		},
		index=expected_index,
	)
	result = pd.concat(
		[result, features[FEATURE_COLUMNS].copy(), target[TARGET_COLUMNS].copy()],
		axis=1,
	)

	numeric_columns = [*FEATURE_COLUMNS, *TARGET_COLUMNS]
	numeric_values = result[numeric_columns].apply(pd.to_numeric, errors="coerce")
	valid_rows = numeric_values.notna().all(axis=1)
	valid_rows &= np.isfinite(numeric_values.to_numpy(dtype=float)).all(axis=1)
	result = result.loc[valid_rows].copy()

	if result.empty:
		return pd.DataFrame(
			{
				"asset_id": pd.Series(dtype="object"),
				"candle_open_ts": pd.Series(dtype=ohlcv["candle_open_ts"].dtype),
				"candle_close_ts": pd.Series(dtype=ohlcv["candle_close_ts"].dtype),
				"decision_ts": pd.Series(dtype=ohlcv["candle_open_ts"].dtype),
				"target_ts": pd.Series(dtype=ohlcv["candle_close_ts"].dtype),
				**{
					column: pd.Series(dtype="float64")
					for column in FEATURE_COLUMNS + ["future_return_1h"]
				},
				"target_direction": pd.Series(dtype="int64"),
			},
			columns=DATASET_COLUMNS,
		)

	result = result[DATASET_COLUMNS]
	result["target_direction"] = result["target_direction"].astype("int64")
	_validate_unique_decision_keys(result)
	result.index = result["decision_ts"]
	return result.reset_index(drop=True)


def write_dataset(dataset: pd.DataFrame, path: str | Path) -> None:
	"""Persist an already-built dataset without building or transforming it."""
	output_path = Path(path)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	dataset.to_parquet(output_path, index=False)
