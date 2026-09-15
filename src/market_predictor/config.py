from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
	"""Raised when the V1 configuration is missing or inconsistent."""


def _require(mapping: dict[str, Any], key: str, path: str) -> Any:
	if key not in mapping:
		raise ConfigError(f"Missing configuration field: {path}.{key}")
	return mapping[key]


def load_v1_config(path: str | Path = "configs/v1.yaml") -> dict[str, Any]:
	"""Load and validate the executable V1 configuration."""
	config_path = Path(path)
	if not config_path.exists():
		raise ConfigError(f"Configuration file not found: {config_path}")

	with config_path.open("r", encoding="utf-8") as file:
		config = yaml.safe_load(file)

	if not isinstance(config, dict):
		raise ConfigError("V1 configuration must be a YAML mapping")

	observation = _require(config, "observation_window", "config")
	horizon = _require(config, "prediction_horizon", "config")
	target = _require(config, "target", "config")
	split = _require(config, "split", "config")
	features = _require(config, "features", "config")

	if config.get("timeframe") != "5m":
		raise ConfigError("config.timeframe must be '5m'")
	if config.get("timezone") != "UTC":
		raise ConfigError("config.timezone must be 'UTC'")
	if observation.get("candles") != 72 or observation.get("minutes") != 360:
		raise ConfigError("config.observation_window must be 72 candles and 360 minutes")
	if horizon.get("candles") != 12 or horizon.get("minutes") != 60:
		raise ConfigError("config.prediction_horizon must be 12 candles and 60 minutes")
	if target.get("type") != "direction" or target.get("return") != "log":
		raise ConfigError("config.target must use direction and log return")
	if target.get("threshold") != 0.0:
		raise ConfigError("config.target.threshold must be 0.0")
	if not isinstance(features, list) or not features:
		raise ConfigError("config.features must be a non-empty list")
	if split.get("method") != "chronological" or split.get("shuffle") is not False:
		raise ConfigError("config.split must be chronological with shuffle=false")

	fractions = [
		split.get("train_fraction"),
		split.get("validation_fraction"),
		split.get("test_fraction"),
	]
	if any(not isinstance(value, (int, float)) for value in fractions) or sum(fractions) != 1.0:
		raise ConfigError("config.split fractions must sum to 1.0")
	if split.get("purge_minutes") != 60:
		raise ConfigError("config.split.purge_minutes must be 60")

	return config
