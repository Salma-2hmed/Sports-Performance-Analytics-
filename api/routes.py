"""
api/routes.py
-------------
RESTful API endpoints for:
  - Athletes   : GET /athletes, POST /athletes, GET/PUT/DELETE /athletes/<id>
  - Performance: POST /athletes/<id>/performance, GET /athletes/<id>/report
  - Analytics  : GET /analytics/pipeline
  - Adapter    : POST /import/<source>   (Adapter pattern demo)
  - Flyweight  : GET  /sports/config      (Flyweight pattern demo)
  - Events     : GET  /events/log         (Observer pattern demo)
"""

from flask import Blueprint, request, jsonify

from utils.auth import require_auth, require_role
from patterns.design_patterns import ExternalDataAdapter, SportConfigFlyweight

athletes_bp = Blueprint("athletes", __name__)
analytics_bp = Blueprint("analytics", __name__)
misc_bp = Blueprint("misc", __name__)


# ── helper injected at app-creation time ──────────────────────────────────────
_service = None
_audit_observer = None
_alert_observer = None


def init_routes(service, audit_obs, alert_obs):
    global _service, _audit_observer, _alert_observer
    _service = service
    _audit_observer = audit_obs
    _alert_observer = alert_obs


# ══════════════════════════════════════════════════════════════════════════════
# ATHLETE CRUD
# ══════════════════════════════════════════════════════════════════════════════
@athletes_bp.route("/athletes", methods=["GET"])
@require_auth
def list_athletes():
    athletes = _service.get_all_athletes()
    return jsonify([a.to_dict() for a in athletes])


@athletes_bp.route("/athletes/<int:athlete_id>", methods=["GET"])
@require_auth
def get_athlete(athlete_id):
    athlete = _service.get_athlete(athlete_id)
    if not athlete:
        return jsonify({"error": "Athlete not found"}), 404
    return jsonify(athlete.to_dict())


@athletes_bp.route("/athletes", methods=["POST"])
@require_role("admin", "coach")
def create_athlete():
    data = request.get_json(force=True)
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    athlete = _service.create_athlete(data)
    return jsonify(athlete.to_dict()), 201


@athletes_bp.route("/athletes/<int:athlete_id>", methods=["PUT"])
@require_role("admin", "coach")
def update_athlete(athlete_id):
    data = request.get_json(force=True)
    athlete = _service.update_athlete(athlete_id, data)
    if not athlete:
        return jsonify({"error": "Athlete not found"}), 404
    return jsonify(athlete.to_dict())


@athletes_bp.route("/athletes/<int:athlete_id>", methods=["DELETE"])
@require_role("admin")
def delete_athlete(athlete_id):
    deleted = _service.delete_athlete(athlete_id)
    if not deleted:
        return jsonify({"error": "Athlete not found"}), 404
    return jsonify({"message": f"Athlete {athlete_id} deleted"}), 200


# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE LOGGING
# ══════════════════════════════════════════════════════════════════════════════
@athletes_bp.route("/athletes/<int:athlete_id>/performance", methods=["POST"])
@require_role("admin", "coach", "analyst")
def log_performance(athlete_id):
    data = request.get_json(force=True)
    metrics = data.get("metrics", {})
    notes = data.get("notes", "")
    if not metrics:
        return jsonify({"error": "metrics dict is required"}), 400
    record = _service.log_performance(athlete_id, metrics, notes)
    return jsonify(record.to_dict()), 201


@athletes_bp.route("/athletes/<int:athlete_id>/report", methods=["GET"])
@require_auth
def get_report(athlete_id):
    # HOF formatters injected at call-time (not hard-coded in service)
    def add_summary(report: dict) -> dict:
        perfs = report.get("performances", [])
        if perfs:
            all_metrics = [list(p["metrics"].values()) for p in perfs]
            flat = [v for sublist in all_metrics for v in sublist]
            report["average_score"] = round(sum(flat) / len(flat), 2) if flat else 0
        return report

    def add_grade(report: dict) -> dict:
        avg = report.get("average_score", 0)
        report["grade"] = (
            "A" if avg >= 85 else
            "B" if avg >= 70 else
            "C" if avg >= 55 else
            "D"
        )
        return report

    report = _service.build_report(athlete_id, [add_summary, add_grade])
    if "error" in report:
        return jsonify(report), 404
    return jsonify(report)


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS — HOF pipeline demo
# ══════════════════════════════════════════════════════════════════════════════
@analytics_bp.route("/analytics/pipeline", methods=["GET"])
@require_auth
def analytics_pipeline():
    sport_filter = request.args.get("sport")
    min_age = int(request.args.get("min_age", 0))

    steps = []
    if sport_filter:
        steps.append(lambda athletes: filter(
            lambda a: a.sport.lower() == sport_filter.lower(), athletes))
    if min_age:
        steps.append(lambda athletes: filter(
            lambda a: a.age >= min_age, athletes))
    steps.append(lambda athletes: map(lambda a: a.to_dict(), athletes))
    steps.append(list)

    result = _service.process_pipeline(*steps)
    return jsonify({
        "filters_applied": {
            "sport": sport_filter,
            "min_age": min_age,
        },
        "count": len(result),
        "athletes": result,
    })


@analytics_bp.route("/analytics/aggregate", methods=["GET"])
@require_auth
def aggregate():
    total_age = _service.aggregate_athletes(
        lambda acc, a: acc + a.age, 0
    )
    athletes = _service.get_all_athletes()
    count = len(athletes)
    return jsonify({
        "total_athletes": count,
        "total_age_sum": total_age,
        "average_age": round(total_age / count, 2) if count else 0,
    })


# ══════════════════════════════════════════════════════════════════════════════
# ADAPTER demo — import from external format
# ══════════════════════════════════════════════════════════════════════════════
@misc_bp.route("/import/<source>", methods=["POST"])
@require_role("admin")
def import_from_source(source):
    raw = request.get_json(force=True)
    adapters = {
        "fifa": ExternalDataAdapter.from_fifa_api,
        "nba": ExternalDataAdapter.from_nba_api,
    }
    if source not in adapters:
        return jsonify({"error": f"Unknown source '{source}'. Use: fifa, nba"}), 400
    adapted = adapters[source](raw)
    athlete = _service.create_athlete(adapted)
    return jsonify({
        "message": f"Imported from {source}",
        "athlete": athlete.to_dict(),
    }), 201


# ══════════════════════════════════════════════════════════════════════════════
# FLYWEIGHT demo
# ══════════════════════════════════════════════════════════════════════════════
@misc_bp.route("/sports/config", methods=["GET"])
@require_auth
def sport_config():
    sport = request.args.get("sport", "Football")
    cfg = SportConfigFlyweight.get(sport)
    return jsonify({
        "sport": cfg.name,
        "max_team_size": cfg.max_team_size,
        "session_duration_min": cfg.session_duration_min,
        "key_metrics": list(cfg.key_metrics),
        "flyweight_pool_size": SportConfigFlyweight.pool_size(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# OBSERVER demo — view audit / alert logs
# ══════════════════════════════════════════════════════════════════════════════
@misc_bp.route("/events/log", methods=["GET"])
@require_role("admin")
def event_log():
    return jsonify({
        "audit_log": _audit_observer.log,
        "performance_alerts": _alert_observer.alerts,
    })
