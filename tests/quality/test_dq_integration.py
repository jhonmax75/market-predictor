from __future__ import annotations

import json

import numpy as np

from market_predictor.quality import validate_dataset


def validate_options():
    return {
        "history_available": True,
        "causal_features": True,
        "scaler_fitted_on_train": True,
        "dataset_version": "v1.0.0",
        "feature_schema_version": "v1.0.0",
    }


def test_dqc_integration_generates_pass_report(valid_dataset, tmp_path):
    frame = valid_dataset.copy()
    frame.loc[50:, "future_return_1h"] = -0.01
    frame.loc[50:, "target_direction"] = np.int8(0)

    report = validate_dataset(frame, **validate_options())
    output = tmp_path / "audit_report.json"
    report.write_json(output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert report.audit_status == "PASS"
    assert payload["audit_status"] == "PASS"
    assert payload["contract_version"] == "DQC-V1.0"
    assert payload["dataset_version"] == "v1.0.0"
    assert payload["feature_schema_version"] == "v1.0.0"
    assert payload["raw_rows"] == len(frame)
    assert payload["results"]
    assert "rejection_count_by_rule" in payload


def test_dqc_integration_preserves_warning_status(zero_volume, tmp_path):
    report = validate_dataset(zero_volume, **validate_options())
    output = tmp_path / "audit_report.json"
    report.write_json(output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert report.audit_status == "PASS_WITH_FLAGS"
    assert payload["audit_status"] == "PASS_WITH_FLAGS"
    assert payload["warning_count"] >= 1


def test_dqc_integration_fails_invalid_dataset(invalid_ohlc):
    report = validate_dataset(invalid_ohlc, **validate_options())

    assert report.audit_status == "FAIL"
    assert report.error_count >= 1
    assert report.rejection_count_by_rule["DQ-011"] >= 1
