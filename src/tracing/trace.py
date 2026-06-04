import json
from datetime import datetime
from typing import Any


class StepTrace:
    def __init__(self):
        self.steps: list[dict] = []
        self.start_time = datetime.now()

    def record(self, step: int, reasoning: str, tool: str, params: Any, result: Any, decision: str):
        result_str = str(result) if result is not None else "None"
        self.steps.append({
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "reasoning": reasoning,
            "tool": tool,
            "params": params,
            "result": result_str[:2000],
            "result_truncated": len(result_str) > 2000,
            "decision": decision,
        })

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_steps": len(self.steps),
            "steps": self.steps,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def readable_summary(self) -> str:
        lines = [f"=== AGENT TRACE ({len(self.steps)} steps) ==="]
        for s in self.steps:
            lines.append(f"\nStep {s['step']}: {s['tool']}")
            lines.append(f"  Reasoning: {s['reasoning'][:200]}")
            lines.append(f"  Decision: {s['decision']}")
        return "\n".join(lines)
