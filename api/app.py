from flask import Flask, request, jsonify
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

    @app.after_request
    def add_cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            from flask import make_response
            r = make_response()
            r.headers["Access-Control-Allow-Origin"] = "*"
            r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            r.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            return r, 200

    db = DatabaseManager()

    bus = EventBus()
    audit_observer = AuditLogObserver()
    alert_observer = PerformanceAlertObserver(threshold=85.0)

    bus.subscribe("athlete_created", audit_observer.on_athlete_created)
    bus.subscribe("athlete_deleted", audit_observer.on_athlete_deleted)
    bus.subscribe("performance_recorded", alert_observer.on_performance_recorded)

    service = AthleteService(db=db, event_bus=bus)


    _seed_demo_data(service)
    init_routes(service, audit_observer, alert_observer)
    app.register_blueprint(athletes_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(misc_bp)

    return app

def _seed_demo_data(service: AthleteService) -> None:
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