"""
api/app.py
----------
Flask application factory.
Wires together: Singleton DB, EventBus, Observers, Service, and Routes.
Demonstrates Dependency Injection (DIP) throughout.
"""

from flask import Flask
from patterns.design_patterns import (
    DatabaseManager,
    EventBus,
    PerformanceAlertObserver,
    AuditLogObserver,
)
from services.athlete_service import AthleteService
from api.routes import athletes_bp, analytics_bp, misc_bp, init_routes


def create_app() -> Flask:
    app = Flask(__name__)

    # ── 1. Singleton DB (one instance for entire app) ──────────────────────
    db = DatabaseManager()

    # ── 2. EventBus + Observers (Observer pattern) ─────────────────────────
    bus = EventBus()
    audit_observer = AuditLogObserver()
    alert_observer = PerformanceAlertObserver(threshold=85.0)

    bus.subscribe("athlete_created", audit_observer.on_athlete_created)
    bus.subscribe("athlete_deleted", audit_observer.on_athlete_deleted)
    bus.subscribe("performance_recorded", alert_observer.on_performance_recorded)

    # ── 3. Service (DIP: receives db + bus, not concrete drivers) ──────────
    service = AthleteService(db=db, event_bus=bus)

    # ── 4. Seed demo data ──────────────────────────────────────────────────
    _seed_demo_data(service)

    # ── 5. Register blueprints ─────────────────────────────────────────────
    init_routes(service, audit_observer, alert_observer)
    app.register_blueprint(athletes_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(misc_bp)

    return app


def _seed_demo_data(service: AthleteService) -> None:
    """Populate in-memory store with sample athletes and performances."""
    athletes_data = [
        {
            "name": "Mohamed Salah", "age": 32, "sport": "Football",
            "team": "Liverpool FC", "nationality": "Egyptian",
            "position": "Forward", "goals": 28, "assists": 10,
        },
        {
            "name": "LeBron James", "age": 39, "sport": "Basketball",
            "team": "LA Lakers", "nationality": "American",
            "position": "Forward", "points_per_game": 25.7,
            "rebounds_per_game": 7.3, "assists_per_game": 8.1,
        },
        {
            "name": "Erling Haaland", "age": 24, "sport": "Football",
            "team": "Man City", "nationality": "Norwegian",
            "position": "Striker", "goals": 36, "assists": 8,
        },
        {
            "name": "Giannis Antetokounmpo", "age": 29, "sport": "Basketball",
            "team": "Milwaukee Bucks", "nationality": "Greek",
            "position": "Center", "points_per_game": 30.4,
            "rebounds_per_game": 11.5, "assists_per_game": 5.9,
        },
    ]

    for data in athletes_data:
        a = service.create_athlete(data)
        service.log_performance(a.id, {
            "speed": 88.0, "endurance": 91.0, "strength": 85.0,
            "agility": 93.0, "recovery": 87.0
        }, notes="Season opener session")
