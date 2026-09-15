from pathlib import Path

from market_predictor.config import load_v1_config


PROJECT_ROOT = Path(__file__).parents[1]


def test_load_v1_config_has_operational_parameters():
    config = load_v1_config(PROJECT_ROOT / "configs" / "v1.yaml")

    assert config["timeframe"] == "5m"
    assert config["timezone"] == "UTC"
    assert config["observation_window"] == {"candles": 72, "minutes": 360}
    assert config["prediction_horizon"] == {"candles": 12, "minutes": 60}
    assert config["target"]["threshold"] == 0.0
    assert config["split"]["method"] == "chronological"
    assert config["split"]["shuffle"] is False
    assert sum(
        config["split"][key]
        for key in ("train_fraction", "validation_fraction", "test_fraction")
    ) == 1.0
    assert len(config["features"]) == 10


def test_load_v1_config_uses_candle_close_as_decision_basis():
    config = load_v1_config(PROJECT_ROOT / "configs" / "v1.yaml")

    assert config["timestamps"]["decision_basis"] == "candle_close"
    assert config["data_quality"]["silent_correction"] is False
