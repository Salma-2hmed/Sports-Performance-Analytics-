"""
models/athlete.py
-----------------
SOLID Principles Applied:
- SRP  : Each class has one responsibility (data storage vs. behavior)
- OCP  : Base Athlete is open for extension, closed for modification
- LSP  : Subclasses (FootballPlayer, BasketballPlayer) are substitutable
         for the base Athlete wherever it is expected
- Runtime Attribute Injection: stats injected dynamically at runtime
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import date


# ── SRP: pure data container ──────────────────────────────────────────────────
@dataclass
class Athlete:
    """Base athlete entity — holds identity data only (SRP)."""
    id: int
    name: str
    age: int
    sport: str
    team: str
    nationality: str
    joined_date: date = field(default_factory=date.today)

    # ── Runtime Attribute Injection ────────────────────────────────────────────
    def inject_stat(self, key: str, value) -> None:
        """Inject arbitrary stats at runtime without modifying the class body."""
        object.__setattr__(self, key, value)

    def get_stat(self, key: str, default=None):
        return getattr(self, key, default)

    def to_dict(self) -> dict:
        base = {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "sport": self.sport,
            "team": self.team,
            "nationality": self.nationality,
            "joined_date": str(self.joined_date),
        }
        # include any runtime-injected attributes
        extras = {
            k: v for k, v in self.__dict__.items()
            if k not in base
        }
        base.update(extras)
        return base


# ── OCP + LSP: extend without modifying Athlete ───────────────────────────────
@dataclass
class FootballPlayer(Athlete):
    """Extends Athlete with football-specific defaults (OCP).
    Is fully substitutable for Athlete (LSP)."""
    position: str = "Unknown"
    goals: int = 0
    assists: int = 0
    matches_played: int = 0

    def __post_init__(self):
        self.sport = "Football"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "position": self.position,
            "goals": self.goals,
            "assists": self.assists,
            "matches_played": self.matches_played,
        })
        return d


@dataclass
class BasketballPlayer(Athlete):
    """Extends Athlete with basketball-specific defaults (OCP / LSP)."""
    position: str = "Unknown"
    points_per_game: float = 0.0
    rebounds_per_game: float = 0.0
    assists_per_game: float = 0.0

    def __post_init__(self):
        self.sport = "Basketball"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "position": self.position,
            "points_per_game": self.points_per_game,
            "rebounds_per_game": self.rebounds_per_game,
            "assists_per_game": self.assists_per_game,
        })
        return d
