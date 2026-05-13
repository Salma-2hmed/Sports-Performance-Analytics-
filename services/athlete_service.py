"""
services/athlete_service.py
----------------------------
SOLID Principles Applied:
- ISP  : Thin interface protocols (IAthleteReader, IAthleteWriter, IPerformanceLogger)
         so clients depend only on what they actually need
- DIP  : AthleteService depends on the abstract DatabaseManager interface,
         not on a concrete database driver
- Higher-Order Functions: processing pipelines built with map/filter/reduce
  and custom HOFs that accept callable strategies at runtime
"""

from typing import Callable, List, Optional, Any, Dict
from functools import reduce
from datetime import date

from models.athlete import Athlete, FootballPlayer, BasketballPlayer
from models.performance import PerformanceRecord
from patterns.design_patterns import (
    DatabaseManager,
    EventBus,
    SportConfigFlyweight,
)


# ══════════════════════════════════════════════════════════════════════════════
# ISP — segregated interface protocols
# ══════════════════════════════════════════════════════════════════════════════
class IAthleteReader:
    """Read-only athlete operations."""
    def get_athlete(self, athlete_id: int) -> Optional[Athlete]: ...
    def get_all_athletes(self) -> List[Athlete]: ...


class IAthleteWriter:
    """Write athlete operations."""
    def create_athlete(self, data: dict) -> Athlete: ...
    def update_athlete(self, athlete_id: int, data: dict) -> Optional[Athlete]: ...
    def delete_athlete(self, athlete_id: int) -> bool: ...


class IPerformanceLogger:
    """Performance recording operations."""
    def log_performance(self, athlete_id: int, metrics: dict,
                        notes: str = "") -> PerformanceRecord: ...
    def get_performances(self, athlete_id: int) -> List[PerformanceRecord]: ...


# ══════════════════════════════════════════════════════════════════════════════
# DIP + Higher-Order Functions — AthleteService
# ══════════════════════════════════════════════════════════════════════════════
class AthleteService(IAthleteReader, IAthleteWriter, IPerformanceLogger):
    """
    Concrete service.  Depends on abstractions (EventBus, DatabaseManager)
    injected via constructor (DIP).
    """

    def __init__(self, db: DatabaseManager, event_bus: EventBus):
        self._db = db                   # DIP: injected, not created here
        self._bus = event_bus           # DIP: injected, not created here

    # ── IAthleteWriter ────────────────────────────────────────────────────────
    def create_athlete(self, data: dict) -> Athlete:
        sport = data.get("sport", "")
        if sport == "Football":
            athlete = FootballPlayer(
                id=0,
                name=data["name"],
                age=data["age"],
                sport="Football",
                team=data.get("team", ""),
                nationality=data.get("nationality", ""),
                position=data.get("position", "Unknown"),
                goals=data.get("goals", 0),
                assists=data.get("assists", 0),
                matches_played=data.get("matches_played", 0),
            )
        elif sport == "Basketball":
            athlete = BasketballPlayer(
                id=0,
                name=data["name"],
                age=data["age"],
                sport="Basketball",
                team=data.get("team", ""),
                nationality=data.get("nationality", ""),
                position=data.get("position", "Unknown"),
                points_per_game=data.get("points_per_game", 0.0),
                rebounds_per_game=data.get("rebounds_per_game", 0.0),
                assists_per_game=data.get("assists_per_game", 0.0),
            )
        else:
            athlete = Athlete(
                id=0,
                name=data["name"],
                age=data["age"],
                sport=sport,
                team=data.get("team", ""),
                nationality=data.get("nationality", ""),
            )

        # runtime attribute injection: attach sport config meta
        config = SportConfigFlyweight.get(sport)
        athlete.inject_stat("sport_config", {
            "max_team_size": config.max_team_size,
            "session_duration_min": config.session_duration_min,
            "key_metrics": list(config.key_metrics),
        })

        saved = self._db.save_athlete(athlete)
        self._bus.publish("athlete_created", saved.to_dict())
        return saved

    def update_athlete(self, athlete_id: int, data: dict) -> Optional[Athlete]:
        athlete = self._db.get_athlete(athlete_id)
        if not athlete:
            return None
        for key, val in data.items():
            if hasattr(athlete, key):
                object.__setattr__(athlete, key, val)
            else:
                athlete.inject_stat(key, val)   # runtime injection for new keys
        self._db.save_athlete(athlete)
        return athlete

    def delete_athlete(self, athlete_id: int) -> bool:
        athlete = self._db.get_athlete(athlete_id)
        if not athlete:
            return False
        deleted = self._db.delete_athlete(athlete_id)
        if deleted:
            self._bus.publish("athlete_deleted", {"id": athlete_id})
        return deleted

    # ── IAthleteReader ────────────────────────────────────────────────────────
    def get_athlete(self, athlete_id: int) -> Optional[Athlete]:
        return self._db.get_athlete(athlete_id)

    def get_all_athletes(self) -> List[Athlete]:
        return self._db.get_all_athletes()

    # ── IPerformanceLogger ────────────────────────────────────────────────────
    def log_performance(self, athlete_id: int, metrics: dict,
                        notes: str = "") -> PerformanceRecord:
        record = PerformanceRecord(
            athlete_id=athlete_id,
            metrics=metrics,
            notes=notes,
        )
        self._db.save_performance(record)
        overall = sum(metrics.values()) / len(metrics) if metrics else 0
        self._bus.publish("performance_recorded", {
            "athlete_id": athlete_id,
            "overall_score": overall,
            "metrics": metrics,
        })
        return record

    def get_performances(self, athlete_id: int) -> List[PerformanceRecord]:
        return self._db.get_performances(athlete_id)

    # ══════════════════════════════════════════════════════════════════════════
    # HIGHER-ORDER FUNCTIONS — processing pipelines
    # ══════════════════════════════════════════════════════════════════════════

    def filter_athletes(self, predicate: Callable[[Athlete], bool]) -> List[Athlete]:
        """HOF: filter athletes by any caller-supplied predicate."""
        return list(filter(predicate, self._db.get_all_athletes()))

    def map_athletes(self, transform: Callable[[Athlete], Any]) -> List[Any]:
        """HOF: transform every athlete using a caller-supplied function."""
        return list(map(transform, self._db.get_all_athletes()))

    def aggregate_athletes(self, reducer: Callable, initial: Any) -> Any:
        """HOF: fold all athletes with a caller-supplied reducer (reduce)."""
        return reduce(reducer, self._db.get_all_athletes(), initial)

    def process_pipeline(self, *steps: Callable) -> List[Any]:
        """
        HOF pipeline: chain arbitrary processing steps.
        Each step receives the output of the previous step.
        Example:
            service.process_pipeline(
                lambda athletes: filter(lambda a: a.age > 25, athletes),
                lambda athletes: map(lambda a: a.to_dict(), athletes),
                list,
            )
        """
        data: Any = self._db.get_all_athletes()
        for step in steps:
            data = step(data)
        return data

    def build_report(self, athlete_id: int,
                     formatters: List[Callable[[dict], dict]]) -> dict:
        """
        HOF: apply a list of formatter functions to enrich a performance report.
        Formatters are composed at call-time, not hard-coded in the service.
        """
        athlete = self._db.get_athlete(athlete_id)
        if not athlete:
            return {"error": "Athlete not found"}
        performances = self._db.get_performances(athlete_id)
        report = {
            "athlete": athlete.to_dict(),
            "total_sessions": len(performances),
            "performances": [p.to_dict() for p in performances],
        }
        for fmt in formatters:
            report = fmt(report)
        return report
