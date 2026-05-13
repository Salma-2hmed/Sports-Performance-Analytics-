"""
patterns/design_patterns.py
----------------------------
Implements four GoF patterns used across the project:

1. Singleton    – DatabaseManager: single shared DB connection
2. Observer     – EventBus + listeners: react to athlete / metric events
3. Adapter      – ExternalDataAdapter: normalise third-party API payloads
4. Flyweight    – SportConfigFlyweight: share immutable sport metadata
"""

import threading
from typing import Callable, Dict, List, Any


# ══════════════════════════════════════════════════════════════════════════════
# 1. SINGLETON — DatabaseManager
# ══════════════════════════════════════════════════════════════════════════════
class DatabaseManager:
    """
    Thread-safe Singleton that owns the in-memory store.
    Only one instance exists for the entire application lifetime.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:          # double-checked locking
                    cls._instance = super().__new__(cls)
                    cls._instance._init_store()
        return cls._instance

    def _init_store(self):
        self._athletes: Dict[int, Any] = {}
        self._performances: List[Any] = []
        self._next_id: int = 1

    # ── CRUD helpers ──────────────────────────────────────────────────────────
    def save_athlete(self, athlete) -> Any:
        if not hasattr(athlete, "id") or athlete.id is None:
            athlete.id = self._next_id
            self._next_id += 1
        self._athletes[athlete.id] = athlete
        return athlete

    def get_athlete(self, athlete_id: int):
        return self._athletes.get(athlete_id)

    def get_all_athletes(self) -> List[Any]:
        return list(self._athletes.values())

    def delete_athlete(self, athlete_id: int) -> bool:
        if athlete_id in self._athletes:
            del self._athletes[athlete_id]
            return True
        return False

    def save_performance(self, record) -> Any:
        self._performances.append(record)
        return record

    def get_performances(self, athlete_id: int) -> List[Any]:
        return [p for p in self._performances if p.athlete_id == athlete_id]


# ══════════════════════════════════════════════════════════════════════════════
# 2. OBSERVER — EventBus
# ══════════════════════════════════════════════════════════════════════════════
class EventBus:
    """
    Publish / subscribe event bus.
    Services subscribe to event types; the bus notifies all subscribers when
    an event is published.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, data: Any = None) -> None:
        for handler in self._subscribers.get(event_type, []):
            handler(data)


# ── Pre-wired observers (concrete listeners) ──────────────────────────────────
class PerformanceAlertObserver:
    """Notifies coaching staff when a metric crosses a threshold."""
    def __init__(self, threshold: float = 90.0):
        self.threshold = threshold
        self.alerts: List[str] = []

    def on_performance_recorded(self, data: dict) -> None:
        score = data.get("overall_score", 0)
        if score >= self.threshold:
            msg = (f"🏅 HIGH PERFORMANCE ALERT: Athlete {data.get('athlete_id')} "
                   f"scored {score:.1f}")
            self.alerts.append(msg)
            print(msg)


class AuditLogObserver:
    """Writes every athlete creation / deletion event to an audit list."""
    def __init__(self):
        self.log: List[str] = []

    def on_athlete_created(self, data: dict) -> None:
        entry = f"[AUDIT] CREATED athlete id={data.get('id')} name={data.get('name')}"
        self.log.append(entry)
        print(entry)

    def on_athlete_deleted(self, data: dict) -> None:
        entry = f"[AUDIT] DELETED athlete id={data.get('id')}"
        self.log.append(entry)
        print(entry)


# ══════════════════════════════════════════════════════════════════════════════
# 3. ADAPTER — ExternalDataAdapter
# ══════════════════════════════════════════════════════════════════════════════
class ExternalDataAdapter:
    """
    Converts heterogeneous third-party payload shapes into the internal
    athlete dict format, so the rest of the system never knows about
    external schemas.
    """

    @staticmethod
    def from_fifa_api(raw: dict) -> dict:
        """Adapt a mock FIFA-style JSON to our internal format."""
        return {
            "name": raw.get("player_name") or raw.get("name", "Unknown"),
            "age": raw.get("player_age") or raw.get("age", 0),
            "sport": "Football",
            "team": raw.get("club") or raw.get("team", "Unknown"),
            "nationality": raw.get("country") or raw.get("nationality", "Unknown"),
            "position": raw.get("pos") or raw.get("position", "Unknown"),
            "goals": raw.get("goals_scored", 0),
            "assists": raw.get("key_assists", 0),
        }

    @staticmethod
    def from_nba_api(raw: dict) -> dict:
        """Adapt a mock NBA-style JSON to our internal format."""
        return {
            "name": raw.get("full_name") or raw.get("name", "Unknown"),
            "age": raw.get("years_old") or raw.get("age", 0),
            "sport": "Basketball",
            "team": raw.get("franchise") or raw.get("team", "Unknown"),
            "nationality": raw.get("country") or raw.get("nationality", "Unknown"),
            "position": raw.get("pos") or raw.get("position", "Unknown"),
            "points_per_game": raw.get("ppg", 0.0),
            "rebounds_per_game": raw.get("rpg", 0.0),
            "assists_per_game": raw.get("apg", 0.0),
        }


# ══════════════════════════════════════════════════════════════════════════════
# 4. FLYWEIGHT — SportConfigFlyweight
# ══════════════════════════════════════════════════════════════════════════════
class SportConfig:
    """Immutable intrinsic state shared across many athlete objects (Flyweight)."""
    __slots__ = ("name", "max_team_size", "session_duration_min", "key_metrics")

    def __init__(self, name: str, max_team_size: int,
                 session_duration_min: int, key_metrics: tuple):
        self.name = name
        self.max_team_size = max_team_size
        self.session_duration_min = session_duration_min
        self.key_metrics = key_metrics


class SportConfigFlyweight:
    """
    Factory that ensures at most one SportConfig object exists per sport name.
    Memory is saved because thousands of athletes share the same SportConfig
    instance rather than each storing duplicate data.
    """
    _pool: Dict[str, SportConfig] = {}

    _defaults = {
        "Football": SportConfig(
            "Football", 11, 90,
            ("goals", "assists", "pass_accuracy", "distance_km")),
        "Basketball": SportConfig(
            "Basketball", 5, 48,
            ("points", "rebounds", "assists", "field_goal_pct")),
        "Tennis": SportConfig(
            "Tennis", 1, 60,
            ("aces", "first_serve_pct", "break_points_won", "winners")),
        "Swimming": SportConfig(
            "Swimming", 1, 30,
            ("time_sec", "stroke_rate", "turns", "distance_m")),
    }

    @classmethod
    def get(cls, sport: str) -> SportConfig:
        if sport not in cls._pool:
            cls._pool[sport] = cls._defaults.get(
                sport,
                SportConfig(sport, 10, 60, ())
            )
        return cls._pool[sport]

    @classmethod
    def pool_size(cls) -> int:
        return len(cls._pool)
