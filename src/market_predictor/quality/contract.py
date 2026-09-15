from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
	ERROR = "ERROR"
	WARNING = "WARNING"
	INFO = "INFO"


class RuleStatus(StrEnum):
	ACCEPT = "ACCEPT"
	REJECT = "REJECT"
	EXCLUDE_ROW = "EXCLUDE_ROW"
	FLAG = "FLAG"
	NOT_EVALUABLE = "NOT_EVALUABLE"


@dataclass(frozen=True)
class RuleSpec:
	rule_id: str
	severity: Severity
	object_name: str
	condition: str
	effect: RuleStatus


@dataclass(frozen=True)
class RuleResult:
	rule_id: str
	severity: Severity
	status: RuleStatus
	message: str
	affected_rows: int = 0


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

TARGET_COLUMNS = ["future_return_1h", "target_direction"]

AUDIT_COLUMNS = [
	"asset_id",
	"decision_ts",
	"candle_open_ts",
	"candle_close_ts",
	"target_ts",
	"dataset_version",
	"feature_schema_version",
]

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]
TIMESTAMP_COLUMNS = [
	"decision_ts",
	"candle_open_ts",
	"candle_close_ts",
	"target_ts",
]


def _rule(
	rule_id: str,
	object_name: str,
	condition: str,
	effect: RuleStatus,
	severity: Severity = Severity.ERROR,
) -> RuleSpec:
	return RuleSpec(rule_id, severity, object_name, condition, effect)


DQC_RULES = (
	_rule("DQ-001", "asset_id", "exists, is a non-empty string", RuleStatus.REJECT),
	_rule("DQ-002", "decision_ts", "exists and is non-null", RuleStatus.REJECT),
	_rule("DQ-003", "timestamps", "are timezone-aware and normalized to UTC", RuleStatus.REJECT),
	_rule("DQ-004", "decision key", "(asset_id, decision_ts) is unique", RuleStatus.REJECT),
	_rule("DQ-005", "decision_ts", "is strictly increasing per asset", RuleStatus.REJECT),
	_rule("DQ-006", "raw candle", "(asset_id, candle_open_ts) is unique", RuleStatus.REJECT),
	_rule("DQ-007", "candle interval", "candle_close_ts - candle_open_ts equals 5 minutes", RuleStatus.REJECT),
	_rule("DQ-008", "candle continuity", "consecutive candles are 5 minutes apart", RuleStatus.EXCLUDE_ROW),
	_rule("DQ-009", "out-of-window gaps", "gaps do not affect candidate rows", RuleStatus.FLAG, Severity.WARNING),
	_rule("DQ-010", "prices", "open, high, low and close are positive", RuleStatus.REJECT),
	_rule("DQ-011", "OHLC", "high/low are consistent with open and close", RuleStatus.REJECT),
	_rule("DQ-012", "volume", "volume is non-negative", RuleStatus.REJECT),
	_rule("DQ-013", "volume", "zero volume is recorded", RuleStatus.FLAG, Severity.WARNING),
	_rule("DQ-014", "OHLCV", "values are finite", RuleStatus.REJECT),
	_rule("DQ-015", "features", "all V1 features are finite", RuleStatus.REJECT),
	_rule("DQ-016", "history", "at least 72 valid historical candles exist", RuleStatus.EXCLUDE_ROW),
	_rule("DQ-017", "feature engineering", "features use data available at decision_ts", RuleStatus.REJECT),
	_rule("DQ-018", "target", "target data exists for supervised rows", RuleStatus.EXCLUDE_ROW),
	_rule("DQ-019", "target_ts", "is exactly one hour after decision_ts", RuleStatus.REJECT),
	_rule("DQ-020", "future_return_1h", "is finite", RuleStatus.REJECT),
	_rule("DQ-021", "target_direction", "matches future_return_1h > 0", RuleStatus.REJECT),
	_rule("DQ-022", "feature schema", "target columns are absent from FEATURE_COLUMNS", RuleStatus.REJECT),
	_rule("DQ-023", "feature engineering", "no future operation contaminates features", RuleStatus.REJECT),
	_rule("DQ-024", "scaler", "is fitted on training data only", RuleStatus.REJECT),
	_rule("DQ-025", "returns", "extreme returns are flagged, not removed", RuleStatus.FLAG, Severity.WARNING),
	_rule("DQ-026", "volume", "extreme volume is flagged, not removed", RuleStatus.FLAG, Severity.WARNING),
	_rule("DQ-027", "features", "final feature columns contain no NaN", RuleStatus.REJECT),
	_rule("DQ-028", "schema", "columns have the declared dtypes", RuleStatus.REJECT),
	_rule("DQ-029", "target distribution", "class degeneracy is reported", RuleStatus.FLAG, Severity.WARNING),
	_rule("DQ-030", "audit report", "a complete report is produced", RuleStatus.REJECT),
)

RULES_BY_ID = {rule.rule_id: rule for rule in DQC_RULES}


def get_rule(rule_id: str) -> RuleSpec:
	return RULES_BY_ID[rule_id]
