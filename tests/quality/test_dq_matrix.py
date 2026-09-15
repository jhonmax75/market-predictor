from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from market_predictor.quality import RuleStatus, validate_dataset


def run_validation(frame: pd.DataFrame, **kwargs):
    options = {
        "history_available": True,
        "causal_features": True,
        "scaler_fitted_on_train": True,
    }
    options.update(kwargs)
    return validate_dataset(frame, **options)


def result_for(report, rule_id: str):
    return next(result for result in report.results if result.rule_id == rule_id)


def test_dq_001_asset_id_required(valid_dataset):
    frame = valid_dataset.copy()
    frame.loc[0, "asset_id"] = ""
    assert result_for(run_validation(frame), "DQ-001").status == RuleStatus.REJECT


def test_dq_002_decision_ts_required(valid_dataset):
    frame = valid_dataset.copy()
    frame.loc[0, "decision_ts"] = pd.NaT
    assert result_for(run_validation(frame), "DQ-002").status == RuleStatus.REJECT


def test_dq_003_timestamps_must_be_utc(naive_timestamp):
    assert result_for(run_validation(naive_timestamp), "DQ-003").status == RuleStatus.REJECT


def test_dq_004_primary_key_must_be_unique(duplicate_primary_key):
    assert result_for(run_validation(duplicate_primary_key), "DQ-004").status == RuleStatus.REJECT


def test_dq_005_decisions_must_be_ordered(valid_dataset):
    frame = valid_dataset.copy()
    frame.loc[1, "decision_ts"] = frame.loc[0, "decision_ts"]
    assert result_for(run_validation(frame), "DQ-005").status == RuleStatus.REJECT


def test_dq_006_candles_must_be_unique(duplicate_candle):
    assert result_for(run_validation(duplicate_candle), "DQ-006").status == RuleStatus.REJECT


def test_dq_007_candle_interval_must_be_five_minutes(valid_dataset):
    frame = valid_dataset.copy()
    frame.loc[0, "candle_close_ts"] += pd.Timedelta(minutes=5)
    assert result_for(run_validation(frame), "DQ-007").status == RuleStatus.REJECT


def test_dq_008_gap_excludes_rows(temporal_gap):
    result = result_for(run_validation(temporal_gap), "DQ-008")
    assert result.status == RuleStatus.EXCLUDE_ROW
    assert result.affected_rows > 0


def test_dq_009_gap_is_flagged(temporal_gap):
    result = result_for(run_validation(temporal_gap), "DQ-009")
    assert result.status == RuleStatus.FLAG
    assert result.severity.value == "WARNING"


@pytest.mark.parametrize("column", ["open", "high", "low", "close"])
def test_dq_010_prices_must_be_positive(valid_dataset, column):
    frame = valid_dataset.copy()
    frame.loc[0, column] = 0
    assert result_for(run_validation(frame), "DQ-010").status == RuleStatus.REJECT


def test_dq_011_ohlc_must_be_consistent(invalid_ohlc):
    assert result_for(run_validation(invalid_ohlc), "DQ-011").status == RuleStatus.REJECT


def test_dq_012_volume_must_be_non_negative(negative_volume):
    assert result_for(run_validation(negative_volume), "DQ-012").status == RuleStatus.REJECT


def test_dq_013_zero_volume_is_only_a_flag(zero_volume):
    result = result_for(run_validation(zero_volume), "DQ-013")
    assert result.status == RuleStatus.FLAG
    assert result.severity.value == "WARNING"


def test_dq_014_ohlcv_must_be_finite(nan_ohlcv):
    assert result_for(run_validation(nan_ohlcv), "DQ-014").status == RuleStatus.REJECT


def test_dq_015_features_must_be_finite(infinite_feature):
    assert result_for(run_validation(infinite_feature), "DQ-015").status == RuleStatus.REJECT


def test_dq_016_history_must_be_verified(valid_dataset):
    result = result_for(run_validation(valid_dataset, history_available=False), "DQ-016")
    assert result.status == RuleStatus.EXCLUDE_ROW


def test_dq_017_causality_is_required(valid_dataset):
    result = result_for(run_validation(valid_dataset, causal_features=False), "DQ-017")
    assert result.status == RuleStatus.REJECT


def test_dq_018_target_must_exist(missing_target):
    result = result_for(run_validation(missing_target), "DQ-018")
    assert result.status == RuleStatus.EXCLUDE_ROW


def test_dq_019_target_must_be_one_hour_after(valid_dataset):
    frame = valid_dataset.copy()
    frame.loc[0, "target_ts"] = frame.loc[0, "decision_ts"] + pd.Timedelta(minutes=30)
    assert result_for(run_validation(frame), "DQ-019").status == RuleStatus.REJECT


def test_dq_020_future_return_must_be_finite(valid_dataset):
    frame = valid_dataset.copy()
    frame.loc[0, "future_return_1h"] = np.inf
    assert result_for(run_validation(frame), "DQ-020").status == RuleStatus.REJECT


def test_dq_021_target_direction_must_match_return(inconsistent_target):
    assert result_for(run_validation(inconsistent_target), "DQ-021").status == RuleStatus.REJECT


def test_dq_022_targets_must_be_outside_features(valid_dataset):
    features = ["ret_5m", "future_return_1h"]
    result = result_for(run_validation(valid_dataset, feature_columns=features), "DQ-022")
    assert result.status == RuleStatus.REJECT


def test_dq_023_future_feature_provenance_fails(valid_dataset):
    result = result_for(run_validation(valid_dataset, causal_features=False), "DQ-023")
    assert result.status == RuleStatus.NOT_EVALUABLE


def test_dq_024_scaler_must_be_fit_on_train(valid_dataset):
    result = result_for(run_validation(valid_dataset, scaler_fitted_on_train=False), "DQ-024")
    assert result.status == RuleStatus.REJECT


def test_dq_025_extreme_return_is_flagged(extreme_return):
    result = result_for(run_validation(extreme_return, extreme_return_threshold=0.20), "DQ-025")
    assert result.status == RuleStatus.FLAG
    assert result.severity.value == "WARNING"


def test_dq_026_extreme_volume_is_flagged(extreme_volume):
    result = result_for(run_validation(extreme_volume, extreme_volume_quantile=0.99), "DQ-026")
    assert result.status == RuleStatus.FLAG


def test_dq_027_final_features_cannot_contain_nan(infinite_feature):
    frame = infinite_feature.copy()
    frame.loc[20, "ret_1h"] = np.nan
    assert result_for(run_validation(frame), "DQ-027").status == RuleStatus.REJECT


def test_dq_028_declared_types_are_checked(valid_dataset):
    frame = valid_dataset.copy()
    frame["target_direction"] = frame["target_direction"].astype(float)
    assert result_for(run_validation(frame), "DQ-028").status == RuleStatus.REJECT


def test_dq_029_class_degeneracy_is_flagged(degenerate_target):
    result = result_for(run_validation(degenerate_target), "DQ-029")
    assert result.status == RuleStatus.FLAG
    assert result.severity.value == "WARNING"


def test_dq_030_report_can_be_serialized(valid_dataset, tmp_path):
    report = run_validation(valid_dataset)
    output = tmp_path / "audit_report.json"
    report.write_json(output)
    payload = output.read_text(encoding="utf-8")
    assert output.exists()
    assert '"audit_status"' in payload
    assert '"results"' in payload
