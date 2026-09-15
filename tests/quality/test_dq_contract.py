import numpy as np
import pandas as pd

from market_predictor.quality import RuleStatus, validate_dataset


def decision_frame() -> pd.DataFrame:
	return pd.DataFrame(
		{
			"asset_id": pd.Series(["BTC", "BTC"], dtype="string"),
			"decision_ts": pd.to_datetime(["2026-01-01 10:00:00", "2026-01-01 10:05:00"], utc=True),
			"candle_open_ts": pd.to_datetime(["2026-01-01 09:55:00", "2026-01-01 10:00:00"], utc=True),
			"candle_close_ts": pd.to_datetime(["2026-01-01 10:00:00", "2026-01-01 10:05:00"], utc=True),
			"target_ts": pd.to_datetime(["2026-01-01 11:00:00", "2026-01-01 11:05:00"], utc=True),
			"open": [100.0, 101.0],
			"high": [102.0, 103.0],
			"low": [99.0, 100.0],
			"close": [101.0, 100.5],
			"volume": [10.0, 11.0],
			"ret_5m": [0.01, -0.005],
			"ret_15m": [0.02, -0.01],
			"ret_1h": [0.03, -0.02],
			"ret_3h": [0.04, -0.03],
			"vol_1h": [0.01, 0.02],
			"vol_6h": [0.02, 0.03],
			"range_5m": [0.03, 0.03],
			"range_1h": [0.05, 0.06],
			"volume_rel_1h": [1.1, 0.9],
			"volume_trend": [1.2, 0.8],
			"future_return_1h": [0.01, -0.01],
			"target_direction": pd.Series([1, 0], dtype="int8"),
		}
	)


def test_valid_supervised_row_passes_contract():
	report = validate_dataset(
		decision_frame(),
		history_available=True,
		causal_features=True,
		scaler_fitted_on_train=True,
		dataset_version="v1.0.0",
		feature_schema_version="v1.0.0",
	)

	assert report.audit_status == "PASS"
	assert report.error_count == 0


def test_invalid_ohlc_fails_contract():
	frame = decision_frame()
	frame.loc[0, "high"] = 98.0

	report = validate_dataset(
		frame,
		history_available=True,
		causal_features=True,
		scaler_fitted_on_train=True,
	)

	assert report.audit_status == "FAIL"
	assert any(result.rule_id == "DQ-011" for result in report.results)


def test_zero_volume_is_a_flag_not_an_error():
	frame = decision_frame()
	frame.loc[0, "volume"] = 0.0

	report = validate_dataset(
		frame,
		history_available=True,
		causal_features=True,
		scaler_fitted_on_train=True,
	)

	zero_volume = next(result for result in report.results if result.rule_id == "DQ-013")
	assert zero_volume.status == RuleStatus.FLAG
	assert report.audit_status == "PASS_WITH_FLAGS"


def test_target_direction_must_match_future_return():
	frame = decision_frame()
	frame.loc[0, "target_direction"] = 0

	report = validate_dataset(
		frame,
		history_available=True,
		causal_features=True,
		scaler_fitted_on_train=True,
	)

	assert report.audit_status == "FAIL"
	assert any(result.rule_id == "DQ-021" for result in report.results)


def test_non_finite_feature_is_rejected():
	frame = decision_frame()
	frame.loc[0, "ret_1h"] = np.inf

	report = validate_dataset(
		frame,
		history_available=True,
		causal_features=True,
		scaler_fitted_on_train=True,
	)

	assert report.audit_status == "FAIL"
	assert any(result.rule_id == "DQ-015" for result in report.results)
