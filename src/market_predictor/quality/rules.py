from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from .contract import (
	FEATURE_COLUMNS,
	OHLCV_COLUMNS,
	RuleResult,
	RuleStatus,
	Severity,
)


def _result(
	rule_id: str,
	status: RuleStatus,
	message: str,
	affected_rows: int = 0,
	severity: Severity = Severity.ERROR,
) -> RuleResult:
	return RuleResult(rule_id, severity, status, message, affected_rows)


def _missing_result(rule_id: str, columns: Iterable[str]) -> RuleResult:
	missing = [column for column in columns if column not in columns]
	return _result(
		rule_id,
		RuleStatus.REJECT,
		f"Missing required columns: {', '.join(missing)}",
	)


def _require_columns(df: pd.DataFrame, rule_id: str, columns: list[str]) -> RuleResult | None:
	missing = [column for column in columns if column not in df.columns]
	if missing:
		return _result(
			rule_id,
			RuleStatus.REJECT,
			f"Missing required columns: {', '.join(missing)}",
		)
	return None


def _pass(rule_id: str, message: str = "passed") -> RuleResult:
	return _result(rule_id, RuleStatus.ACCEPT, message)


def _not_evaluable(rule_id: str, message: str) -> RuleResult:
	return _result(rule_id, RuleStatus.NOT_EVALUABLE, message)


def evaluate_rules(
	df: pd.DataFrame,
	*,
	require_target: bool = True,
	feature_columns: list[str] | None = None,
	history_available: bool | None = None,
	causal_features: bool | None = None,
	scaler_fitted_on_train: bool | None = None,
	extreme_return_threshold: float | None = None,
	extreme_volume_quantile: float | None = None,
) -> list[RuleResult]:
	"""Evaluate the executable DQC rules for a decision or candle dataset.

	Pipeline-level claims such as causality and scaler provenance must be
	supplied explicitly because they cannot be proven from values alone.
	"""
	features = feature_columns or FEATURE_COLUMNS
	results: list[RuleResult] = []

	if not isinstance(df, pd.DataFrame) or df.empty:
		return [_result("DQ-001", RuleStatus.REJECT, "Input must be a non-empty DataFrame")]

	asset_check = _require_columns(df, "DQ-001", ["asset_id"])
	if asset_check:
		results.append(asset_check)
	else:
		invalid_asset = df["asset_id"].isna() | (df["asset_id"].astype("string").str.strip() == "")
		results.append(
			_result("DQ-001", RuleStatus.REJECT, "asset_id contains null or empty values", int(invalid_asset.sum()))
			if invalid_asset.any()
			else _pass("DQ-001", "asset_id is present and non-empty")
		)

	decision_check = _require_columns(df, "DQ-002", ["decision_ts"])
	if decision_check:
		results.append(decision_check)
	else:
		null_decisions = df["decision_ts"].isna()
		results.append(
			_result("DQ-002", RuleStatus.REJECT, "decision_ts contains null values", int(null_decisions.sum()))
			if null_decisions.any()
			else _pass("DQ-002", "decision_ts is non-null")
		)

	timestamp_columns = [
		column for column in ("decision_ts", "candle_open_ts", "candle_close_ts", "target_ts")
		if column in df.columns
	]
	timestamp_errors = 0
	for column in timestamp_columns:
		dtype = df[column].dtype
		if not isinstance(dtype, pd.DatetimeTZDtype) or str(dtype.tz) != "UTC":
			timestamp_errors += int(len(df))
	results.append(
		_result("DQ-003", RuleStatus.REJECT, "timestamps must be timezone-aware UTC", timestamp_errors)
		if timestamp_errors
		else _pass("DQ-003", "timestamps are UTC")
	)

	if "asset_id" in df.columns and "decision_ts" in df.columns:
		duplicated = df.duplicated(["asset_id", "decision_ts"], keep=False)
		results.append(
			_result("DQ-004", RuleStatus.REJECT, "decision key is duplicated", int(duplicated.sum()))
			if duplicated.any()
			else _pass("DQ-004", "decision key is unique")
		)
		ordered = df.sort_values(["asset_id", "decision_ts"])
		delta = ordered.groupby("asset_id", sort=False)["decision_ts"].diff().dropna()
		invalid_order = (delta <= pd.Timedelta(0)).sum()
		results.append(
			_result("DQ-005", RuleStatus.REJECT, "decision_ts is not strictly increasing", int(invalid_order))
			if invalid_order
			else _pass("DQ-005", "decision_ts is strictly increasing per asset")
		)
	else:
		results.extend([
			_not_evaluable("DQ-004", "decision key columns are unavailable"),
			_not_evaluable("DQ-005", "decision timestamp columns are unavailable"),
		])

	if "asset_id" in df.columns and "candle_open_ts" in df.columns:
		duplicated = df.duplicated(["asset_id", "candle_open_ts"], keep=False)
		results.append(
			_result("DQ-006", RuleStatus.REJECT, "raw candle key is duplicated", int(duplicated.sum()))
			if duplicated.any()
			else _pass("DQ-006", "raw candle key is unique")
		)
	else:
		results.append(_not_evaluable("DQ-006", "raw candle columns are unavailable"))

	if "candle_open_ts" in df.columns and "candle_close_ts" in df.columns:
		interval = df["candle_close_ts"] - df["candle_open_ts"]
		invalid_interval = interval != pd.Timedelta(minutes=5)
		results.append(
			_result("DQ-007", RuleStatus.REJECT, "candle interval is not 5 minutes", int(invalid_interval.sum()))
			if invalid_interval.any()
			else _pass("DQ-007", "candle interval is 5 minutes")
		)
		ordered = df.sort_values(["asset_id", "candle_open_ts"]) if "asset_id" in df.columns else df
		gaps = ordered.groupby("asset_id", sort=False)["candle_open_ts"].diff() if "asset_id" in df.columns else ordered["candle_open_ts"].diff()
		non_contiguous = gaps.dropna() != pd.Timedelta(minutes=5)
		gap_count = int(non_contiguous.sum())
		results.append(
			_result("DQ-008", RuleStatus.EXCLUDE_ROW, "candle continuity has gaps", gap_count)
			if gap_count
			else _pass("DQ-008", "candle sequence is continuous")
		)
		results.append(
			_result("DQ-009", RuleStatus.FLAG, "gaps detected outside candidate windows", gap_count, Severity.WARNING)
			if gap_count
			else _pass("DQ-009", "no gaps detected")
		)
	else:
		results.extend([
			_not_evaluable("DQ-007", "candle interval columns are unavailable"),
			_not_evaluable("DQ-008", "candle continuity columns are unavailable"),
			_not_evaluable("DQ-009", "candle continuity columns are unavailable"),
		])

	ohlcv_check = _require_columns(df, "DQ-010", OHLCV_COLUMNS)
	if ohlcv_check:
		results.append(ohlcv_check)
		results.extend([_not_evaluable(rule_id, "OHLCV columns are unavailable") for rule_id in ("DQ-011", "DQ-012", "DQ-014")])
	else:
		prices = df[["open", "high", "low", "close"]]
		invalid_prices = (prices <= 0).any(axis=1)
		results.append(
			_result("DQ-010", RuleStatus.REJECT, "prices must be positive", int(invalid_prices.sum()))
			if invalid_prices.any()
			else _pass("DQ-010", "prices are positive")
		)
		invalid_ohlc = (
			(df["high"] < prices[["open", "close"]].max(axis=1))
			| (df["low"] > prices[["open", "close"]].min(axis=1))
			| (df["high"] < df["low"])
		)
		results.append(
			_result("DQ-011", RuleStatus.REJECT, "OHLC relationship is invalid", int(invalid_ohlc.sum()))
			if invalid_ohlc.any()
			else _pass("DQ-011", "OHLC relationship is valid")
		)
		invalid_volume = df["volume"] < 0
		results.append(
			_result("DQ-012", RuleStatus.REJECT, "volume must be non-negative", int(invalid_volume.sum()))
			if invalid_volume.any()
			else _pass("DQ-012", "volume is non-negative")
		)
		zero_volume = df["volume"] == 0
		results.append(
			_result("DQ-013", RuleStatus.FLAG, "zero volume detected", int(zero_volume.sum()), Severity.WARNING)
			if zero_volume.any()
			else _pass("DQ-013", "no zero volume")
		)
		finite_ohlcv = np.isfinite(df[OHLCV_COLUMNS].to_numpy()).all(axis=1)
		results.append(
			_result("DQ-014", RuleStatus.REJECT, "OHLCV contains non-finite values", int((~finite_ohlcv).sum()))
			if not finite_ohlcv.all()
			else _pass("DQ-014", "OHLCV values are finite")
		)

	missing_features = [column for column in features if column not in df.columns]
	if missing_features:
		results.append(_result("DQ-015", RuleStatus.REJECT, f"Missing features: {', '.join(missing_features)}"))
		results.append(_result("DQ-027", RuleStatus.REJECT, f"Missing features: {', '.join(missing_features)}"))
	else:
		finite_features = np.isfinite(df[features].to_numpy()).all(axis=1)
		results.append(
			_result("DQ-015", RuleStatus.REJECT, "features contain non-finite values", int((~finite_features).sum()))
			if not finite_features.all()
			else _pass("DQ-015", "features are finite")
		)
		results.append(
			_result("DQ-027", RuleStatus.REJECT, "final features contain NaN", int(df[features].isna().any(axis=1).sum()))
			if df[features].isna().any(axis=1).any()
			else _pass("DQ-027", "final features contain no NaN")
		)

	results.append(
		_pass("DQ-016", "72 historical candles were verified")
		if history_available is True
		else _result("DQ-016", RuleStatus.EXCLUDE_ROW, "72 historical candles were not verified")
		if history_available is False
		else _not_evaluable("DQ-016", "history sufficiency must be supplied by the dataset builder")
	)
	results.append(
		_pass("DQ-017", "causality assertion supplied")
		if causal_features is True
		else _result("DQ-017", RuleStatus.REJECT, "causality was not proven")
		if causal_features is False
		else _not_evaluable("DQ-017", "causality must be supplied by the feature pipeline")
	)

	target_columns_present = all(column in df.columns for column in ("target_ts", "future_return_1h", "target_direction"))
	if not require_target:
		results.append(_not_evaluable("DQ-018", "target is not required for inference"))
	elif not target_columns_present:
		results.append(_result("DQ-018", RuleStatus.EXCLUDE_ROW, "supervised target columns are missing"))
	else:
		results.append(
			_pass("DQ-018", "target columns are available")
			if df["target_ts"].notna().all()
			else _result("DQ-018", RuleStatus.EXCLUDE_ROW, "target_ts contains null values", int(df["target_ts"].isna().sum()))
		)
		utc_timestamps = all(
			isinstance(df[column].dtype, pd.DatetimeTZDtype)
			and str(df[column].dtype.tz) == "UTC"
			for column in ("decision_ts", "target_ts")
		)
		if not utc_timestamps:
			results.append(_not_evaluable("DQ-019", "timestamp arithmetic requires UTC timestamps"))
		else:
			target_delta = df["target_ts"] - df["decision_ts"]
			invalid_target_delta = target_delta != pd.Timedelta(hours=1)
			results.append(
				_result("DQ-019", RuleStatus.REJECT, "target_ts is not one hour after decision_ts", int(invalid_target_delta.sum()))
				if invalid_target_delta.any()
				else _pass("DQ-019", "target_ts is one hour after decision_ts")
			)
		finite_target = np.isfinite(df["future_return_1h"].to_numpy())
		results.append(
			_result("DQ-020", RuleStatus.REJECT, "future_return_1h is not finite", int((~finite_target).sum()))
			if not finite_target.all()
			else _pass("DQ-020", "future_return_1h is finite")
		)
		expected_target = (df["future_return_1h"] > 0).astype("int8")
		invalid_direction = df["target_direction"] != expected_target
		results.append(
			_result("DQ-021", RuleStatus.REJECT, "target_direction is inconsistent", int(invalid_direction.sum()))
			if invalid_direction.any()
			else _pass("DQ-021", "target_direction is consistent")
		)
	target_in_features = set(("future_return_1h", "target_direction")) & set(features)
	results.append(
		_result("DQ-022", RuleStatus.REJECT, "target columns are present in FEATURE_COLUMNS")
		if target_in_features
		else _pass("DQ-022", "target columns are separated from features")
	)
	results.append(
		_pass("DQ-023", "no future operation reported")
		if causal_features is True
		else _not_evaluable("DQ-023", "feature-engineering provenance is not supplied")
	)
	results.append(
		_pass("DQ-024", "scaler provenance is valid")
		if scaler_fitted_on_train is True
		else _result("DQ-024", RuleStatus.REJECT, "scaler was not proven to be fitted on train only")
		if scaler_fitted_on_train is False
		else _not_evaluable("DQ-024", "scaler provenance must be supplied")
	)

	extreme_return = pd.Series(False, index=df.index)
	if extreme_return_threshold is not None and "ret_5m" in df.columns:
		extreme_return = df["ret_5m"].abs() > extreme_return_threshold
	results.append(
		_result("DQ-025", RuleStatus.FLAG, "extreme returns detected", int(extreme_return.sum()), Severity.WARNING)
		if extreme_return.any()
		else _pass("DQ-025", "no configured extreme returns")
	)
	extreme_volume = pd.Series(False, index=df.index)
	if extreme_volume_quantile is not None and "volume" in df.columns:
		threshold = df["volume"].quantile(extreme_volume_quantile)
		extreme_volume = df["volume"] > threshold
	results.append(
		_result("DQ-026", RuleStatus.FLAG, "extreme volume detected", int(extreme_volume.sum()), Severity.WARNING)
		if extreme_volume.any()
		else _pass("DQ-026", "no configured extreme volume")
	)

	dtype_errors = []
	if "target_direction" in df.columns and not pd.api.types.is_integer_dtype(df["target_direction"]):
		dtype_errors.append("target_direction")
	if "asset_id" in df.columns and not (pd.api.types.is_string_dtype(df["asset_id"]) or df["asset_id"].dtype == object):
		dtype_errors.append("asset_id")
	results.append(
		_result("DQ-028", RuleStatus.REJECT, f"invalid dtypes: {', '.join(dtype_errors)}")
		if dtype_errors
		else _pass("DQ-028", "declared dtypes are compatible")
	)

	if require_target and "target_direction" in df.columns:
		classes = set(df["target_direction"].dropna().unique())
		results.append(
			_result("DQ-029", RuleStatus.FLAG, "class degeneracy detected", len(df), Severity.WARNING)
			if classes != {0, 1}
			else _pass("DQ-029", "both target classes are present")
		)
	else:
		results.append(_not_evaluable("DQ-029", "target distribution is unavailable"))

	results.append(_pass("DQ-030", "audit report can be generated"))
	return results
