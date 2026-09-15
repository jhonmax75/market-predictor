from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .contract import RuleResult, RuleStatus, Severity


@dataclass
class AuditReport:
	contract_version: str = "DQC-V1.0"
	dataset_version: str | None = None
	feature_schema_version: str | None = None
	raw_rows: int = 0
	accepted_rows: int = 0
	excluded_rows: int = 0
	rejected_rows: int = 0
	purged_rows: int = 0
	results: list[RuleResult] = field(default_factory=list)
	metadata: dict[str, Any] = field(default_factory=dict)

	@property
	def error_count(self) -> int:
		return sum(
			1
			for result in self.results
			if result.severity == Severity.ERROR
			and result.status in {
				RuleStatus.REJECT,
				RuleStatus.EXCLUDE_ROW,
				RuleStatus.NOT_EVALUABLE,
			}
		)

	@property
	def warning_count(self) -> int:
		return sum(1 for result in self.results if result.severity == Severity.WARNING and result.status == RuleStatus.FLAG)

	@property
	def audit_status(self) -> str:
		if self.error_count:
			return "FAIL"
		if self.warning_count:
			return "PASS_WITH_FLAGS"
		return "PASS"

	@property
	def rejection_count_by_rule(self) -> dict[str, int]:
		return {
			result.rule_id: result.affected_rows
			for result in self.results
			if result.status in {RuleStatus.REJECT, RuleStatus.EXCLUDE_ROW, RuleStatus.FLAG}
			and result.affected_rows > 0
		}

	def to_dict(self) -> dict[str, Any]:
		payload = asdict(self)
		payload["results"] = [asdict(result) for result in self.results]
		payload["error_count"] = self.error_count
		payload["warning_count"] = self.warning_count
		payload["rejection_count_by_rule"] = self.rejection_count_by_rule
		payload["audit_status"] = self.audit_status
		return payload

	def write_json(self, path: str | Path) -> None:
		output_path = Path(path)
		output_path.parent.mkdir(parents=True, exist_ok=True)
		output_path.write_text(
			json.dumps(self.to_dict(), indent=2, ensure_ascii=True, default=str),
			encoding="utf-8",
		)
