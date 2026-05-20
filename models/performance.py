"""
models/performance.py
---------------------
SRP: PerformanceRecord is responsible only for holding one metric snapshot.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any


@dataclass
class PerformanceRecord:
    athlete_id: int
    session_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "athlete_id": self.athlete_id,
            "session_date": self.session_date.isoformat(),
            "metrics": self.metrics,
            "notes": self.notes,
        }
