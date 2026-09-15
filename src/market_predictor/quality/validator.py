from __future__ import annotations

import pandas as pd

from .report import AuditReport
from .rules import evaluate_rules


def validate_dataset(
	df: pd.DataFrame,
	*,
	require_target: bool = True,
	feature_columns: list[str] | None = None,
	history_available: bool | None = None,
	causal_features: bool | None = None,
	scaler_fitted_on_train: bool | None = None,
	extreme_return_threshold: float | None = None,
	extreme_volume_quantile: float | None = None,
	dataset_version: str | None = None,
	feature_schema_version: str | None = None,
) -> AuditReport:
	"""Run the DQC V1 contract and return an auditable report."""
	results = evaluate_rules(
		df,
		require_target=require_target,
		feature_columns=feature_columns,
		history_available=history_available,
		causal_features=causal_features,
		scaler_fitted_on_train=scaler_fitted_on_train,
		extreme_return_threshold=extreme_return_threshold,
		extreme_volume_quantile=extreme_volume_quantile,
	)
	report = AuditReport(
		dataset_version=dataset_version,
		feature_schema_version=feature_schema_version,
		raw_rows=len(df) if isinstance(df, pd.DataFrame) else 0,
		results=results,
	)
	report.accepted_rows = report.raw_rows if report.audit_status != "FAIL" else 0
	report.excluded_rows = sum(
		result.affected_rows
		for result in results
		if result.status == result.status.EXCLUDE_ROW
	)
	report.rejected_rows = sum(
		result.affected_rows
		for result in results
		if result.status == result.status.REJECT
	)
	return report


validate = validate_dataset
