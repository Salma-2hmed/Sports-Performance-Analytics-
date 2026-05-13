"""
tests/test_project.py
---------------------
Comprehensive tests for:
  - SOLID principles (SRP, OCP, LSP, ISP, DIP)
  - Design patterns (Singleton, Observer, Adapter, Flyweight)
  - Higher-Order Functions pipeline
  - REST API (all CRUD + special endpoints)
  - Runtime Attribute Injection
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
from datetime import date

from models.athlete import Athlete, FootballPlayer, BasketballPlayer
from models.performance import PerformanceRecord
from patterns.design_patterns import (
    DatabaseManager, EventBus,
    PerformanceAlertObserver, AuditLogObserver,
    ExternalDataAdapter, SportConfigFlyweight,
)
from services.athlete_service import AthleteService
from api.app import create_app


# ══════════════════════════════════════════════════════════════════════════════
class TestModels(unittest.TestCase):
    """SRP, OCP, LSP — model layer."""

    def test_base_athlete_srp(self):
        """Athlete only holds data — SRP."""
        a = Athlete(1, "Ali", 25, "Football", "Al Ahly", "Egyptian")
        self.assertEqual(a.name, "Ali")
        self.assertIn("name", a.to_dict())

    def test_football_player_ocp(self):
        """FootballPlayer extends Athlete without modifying it — OCP."""
        fp = FootballPlayer(2, "Salah", 32, "Football", "Liverpool", "Egyptian",
                            position="Forward", goals=28)
        d = fp.to_dict()
        self.assertEqual(d["goals"], 28)
        self.assertEqual(d["sport"], "Football")

    def test_basketball_player_lsp(self):
        """BasketballPlayer is a valid Athlete substitute — LSP."""
        bp = BasketballPlayer(3, "LeBron", 39, "Basketball", "Lakers", "American",
                              points_per_game=25.7)

        def print_name(athlete: Athlete) -> str:
            return athlete.name

        self.assertEqual(print_name(bp), "LeBron")  # LSP: accepted as Athlete

    def test_runtime_attribute_injection(self):
        """inject_stat adds attributes at runtime."""
        a = Athlete(4, "Test", 20, "Tennis", "Team", "EG")
        a.inject_stat("aces", 12)
        self.assertEqual(a.get_stat("aces"), 12)
        self.assertIn("aces", a.to_dict())


# ══════════════════════════════════════════════════════════════════════════════
class TestSingleton(unittest.TestCase):
    """Singleton pattern — DatabaseManager."""

    def test_same_instance(self):
        db1 = DatabaseManager()
        db2 = DatabaseManager()
        self.assertIs(db1, db2)

    def test_shared_state(self):
        db1 = DatabaseManager()
        a = Athlete(99, "Shared", 25, "Football", "Team", "EG")
        db1.save_athlete(a)
        db2 = DatabaseManager()
        self.assertIsNotNone(db2.get_athlete(99))


# ══════════════════════════════════════════════════════════════════════════════
class TestObserver(unittest.TestCase):
    """Observer pattern — EventBus, AuditLogObserver, PerformanceAlertObserver."""

    def setUp(self):
        self.bus = EventBus()
        self.audit = AuditLogObserver()
        self.alert = PerformanceAlertObserver(threshold=80.0)
        self.bus.subscribe("athlete_created", self.audit.on_athlete_created)
        self.bus.subscribe("athlete_deleted", self.audit.on_athlete_deleted)
        self.bus.subscribe("performance_recorded", self.alert.on_performance_recorded)

    def test_audit_on_create(self):
        self.bus.publish("athlete_created", {"id": 1, "name": "Omar"})
        self.assertTrue(any("CREATED" in e for e in self.audit.log))

    def test_audit_on_delete(self):
        self.bus.publish("athlete_deleted", {"id": 1})
        self.assertTrue(any("DELETED" in e for e in self.audit.log))

    def test_alert_on_high_performance(self):
        self.bus.publish("performance_recorded",
                         {"athlete_id": 1, "overall_score": 95.0})
        self.assertTrue(len(self.alert.alerts) > 0)

    def test_no_alert_below_threshold(self):
        before = len(self.alert.alerts)
        self.bus.publish("performance_recorded",
                         {"athlete_id": 2, "overall_score": 50.0})
        self.assertEqual(len(self.alert.alerts), before)


# ══════════════════════════════════════════════════════════════════════════════
class TestAdapter(unittest.TestCase):
    """Adapter pattern — ExternalDataAdapter."""

    def test_fifa_adapter(self):
        raw = {"player_name": "Messi", "player_age": 37,
               "club": "Inter Miami", "country": "Argentina",
               "pos": "Forward", "goals_scored": 20, "key_assists": 15}
        adapted = ExternalDataAdapter.from_fifa_api(raw)
        self.assertEqual(adapted["name"], "Messi")
        self.assertEqual(adapted["sport"], "Football")
        self.assertEqual(adapted["goals"], 20)

    def test_nba_adapter(self):
        raw = {"full_name": "Curry", "years_old": 36,
               "franchise": "Warriors", "country": "American",
               "pos": "PG", "ppg": 29.4, "rpg": 6.1, "apg": 6.3}
        adapted = ExternalDataAdapter.from_nba_api(raw)
        self.assertEqual(adapted["name"], "Curry")
        self.assertEqual(adapted["sport"], "Basketball")
        self.assertEqual(adapted["points_per_game"], 29.4)


# ══════════════════════════════════════════════════════════════════════════════
class TestFlyweight(unittest.TestCase):
    """Flyweight pattern — SportConfigFlyweight."""

    def test_same_object_returned(self):
        cfg1 = SportConfigFlyweight.get("Football")
        cfg2 = SportConfigFlyweight.get("Football")
        self.assertIs(cfg1, cfg2)

    def test_different_sports_different_objects(self):
        cfg_fb = SportConfigFlyweight.get("Football")
        cfg_bb = SportConfigFlyweight.get("Basketball")
        self.assertIsNot(cfg_fb, cfg_bb)

    def test_config_values(self):
        cfg = SportConfigFlyweight.get("Football")
        self.assertEqual(cfg.max_team_size, 11)
        self.assertIn("goals", cfg.key_metrics)


# ══════════════════════════════════════════════════════════════════════════════
class TestService(unittest.TestCase):
    """Service layer: DIP, ISP, HOF."""

    def setUp(self):
        # fresh isolated bus + service (DIP: injected)
        self.bus = EventBus()
        self.audit = AuditLogObserver()
        self.bus.subscribe("athlete_created", self.audit.on_athlete_created)
        self.db = DatabaseManager()
        self.service = AthleteService(db=self.db, event_bus=self.bus)

    def test_create_and_get(self):
        a = self.service.create_athlete({
            "name": "Karim", "age": 27, "sport": "Football",
            "team": "Zamalek", "nationality": "Egyptian"
        })
        fetched = self.service.get_athlete(a.id)
        self.assertEqual(fetched.name, "Karim")

    def test_hof_filter(self):
        self.service.create_athlete({
            "name": "Young", "age": 18, "sport": "Tennis",
            "team": "Solo", "nationality": "EG"
        })
        old = self.service.filter_athletes(lambda a: a.age > 25)
        for athlete in old:
            self.assertGreater(athlete.age, 25)

    def test_hof_map(self):
        names = self.service.map_athletes(lambda a: a.name)
        self.assertIsInstance(names, list)
        self.assertTrue(all(isinstance(n, str) for n in names))

    def test_hof_aggregate(self):
        total = self.service.aggregate_athletes(
            lambda acc, a: acc + a.age, 0)
        self.assertIsInstance(total, int)

    def test_hof_pipeline(self):
        result = self.service.process_pipeline(
            lambda athletes: filter(lambda a: a.age > 0, athletes),
            lambda athletes: map(lambda a: a.to_dict(), athletes),
            list,
        )
        self.assertIsInstance(result, list)

    def test_performance_log_and_report(self):
        a = self.service.create_athlete({
            "name": "Swimmer", "age": 22, "sport": "Swimming",
            "team": "AquaFC", "nationality": "EG"
        })
        self.service.log_performance(a.id, {"speed": 90, "form": 85})
        report = self.service.build_report(a.id, [])
        self.assertGreaterEqual(report["total_sessions"], 1)

    def test_observer_fires_on_create(self):
        before = len(self.audit.log)
        self.service.create_athlete({
            "name": "Observer Test", "age": 25, "sport": "Football",
            "team": "Test FC", "nationality": "EG"
        })
        self.assertGreater(len(self.audit.log), before)


# ══════════════════════════════════════════════════════════════════════════════
class TestAPI(unittest.TestCase):
    """REST API: CRUD + auth + special endpoints."""

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.admin_headers = {"Authorization": "Bearer admin-token-001"}
        self.coach_headers = {"Authorization": "Bearer coach-token-002"}
        self.analyst_headers = {"Authorization": "Bearer analyst-token-003"}

    def test_list_athletes_requires_auth(self):
        r = self.client.get("/athletes")
        self.assertEqual(r.status_code, 401)

    def test_list_athletes_authenticated(self):
        r = self.client.get("/athletes", headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIsInstance(data, list)

    def test_create_athlete(self):
        payload = {
            "name": "New Player", "age": 24, "sport": "Football",
            "team": "Test FC", "nationality": "EG"
        }
        r = self.client.post("/athletes", json=payload,
                             headers=self.admin_headers)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["name"], "New Player")

    def test_create_requires_name(self):
        r = self.client.post("/athletes", json={"age": 25},
                             headers=self.admin_headers)
        self.assertEqual(r.status_code, 400)

    def test_get_single_athlete(self):
        create_r = self.client.post("/athletes",
                                    json={"name": "Solo", "age": 22,
                                          "sport": "Tennis",
                                          "team": "Solo", "nationality": "EG"},
                                    headers=self.admin_headers)
        aid = create_r.get_json()["id"]
        r = self.client.get(f"/athletes/{aid}", headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["id"], aid)

    def test_update_athlete(self):
        create_r = self.client.post("/athletes",
                                    json={"name": "Old Name", "age": 20,
                                          "sport": "Football",
                                          "team": "T", "nationality": "EG"},
                                    headers=self.admin_headers)
        aid = create_r.get_json()["id"]
        r = self.client.put(f"/athletes/{aid}", json={"name": "New Name"},
                            headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["name"], "New Name")

    def test_delete_athlete(self):
        create_r = self.client.post("/athletes",
                                    json={"name": "To Delete", "age": 25,
                                          "sport": "Football",
                                          "team": "T", "nationality": "EG"},
                                    headers=self.admin_headers)
        aid = create_r.get_json()["id"]
        r = self.client.delete(f"/athletes/{aid}", headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)

    def test_analyst_cannot_delete(self):
        create_r = self.client.post("/athletes",
                                    json={"name": "Protected", "age": 25,
                                          "sport": "Football",
                                          "team": "T", "nationality": "EG"},
                                    headers=self.admin_headers)
        aid = create_r.get_json()["id"]
        r = self.client.delete(f"/athletes/{aid}", headers=self.analyst_headers)
        self.assertEqual(r.status_code, 403)

    def test_log_performance(self):
        create_r = self.client.post("/athletes",
                                    json={"name": "Perf Player", "age": 26,
                                          "sport": "Basketball",
                                          "team": "BB", "nationality": "US"},
                                    headers=self.admin_headers)
        aid = create_r.get_json()["id"]
        r = self.client.post(f"/athletes/{aid}/performance",
                             json={"metrics": {"speed": 90, "power": 80}},
                             headers=self.admin_headers)
        self.assertEqual(r.status_code, 201)

    def test_report_endpoint(self):
        create_r = self.client.post("/athletes",
                                    json={"name": "Reporter", "age": 28,
                                          "sport": "Football",
                                          "team": "T", "nationality": "EG"},
                                    headers=self.admin_headers)
        aid = create_r.get_json()["id"]
        self.client.post(f"/athletes/{aid}/performance",
                         json={"metrics": {"x": 90, "y": 80}},
                         headers=self.admin_headers)
        r = self.client.get(f"/athletes/{aid}/report",
                            headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        self.assertIn("grade", r.get_json())

    def test_analytics_pipeline(self):
        r = self.client.get("/analytics/pipeline?sport=Football",
                            headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("athletes", d)

    def test_analytics_aggregate(self):
        r = self.client.get("/analytics/aggregate",
                            headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        self.assertIn("average_age", r.get_json())

    def test_import_fifa(self):
        raw = {"player_name": "Zidane", "player_age": 52,
               "club": "Real Madrid", "country": "French",
               "pos": "Midfielder", "goals_scored": 0, "key_assists": 0}
        r = self.client.post("/import/fifa", json=raw,
                             headers=self.admin_headers)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["athlete"]["name"], "Zidane")

    def test_flyweight_config_endpoint(self):
        r = self.client.get("/sports/config?sport=Basketball",
                            headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertEqual(d["sport"], "Basketball")
        self.assertEqual(d["max_team_size"], 5)

    def test_event_log_endpoint(self):
        r = self.client.get("/events/log", headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("audit_log", d)
        self.assertIn("performance_alerts", d)

    def test_invalid_token(self):
        r = self.client.get("/athletes",
                            headers={"Authorization": "Bearer wrong-token"})
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
