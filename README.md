# Sports Performance Analytics — Project 48

A Python REST API demonstrating all major software engineering concepts required
for the module: **SOLID principles**, **Design Patterns**, **Higher-Order Functions**,
**RESTful API with authentication**, and **Runtime Attribute Injection**.

---

## Project Structure

```
sports_analytics/
├── main.py                        ← Entry point (Flask dev server)
├── models/
│   ├── athlete.py                 ← SRP · OCP · LSP · Runtime Injection
│   └── performance.py             ← SRP (single-purpose data record)
├── patterns/
│   └── design_patterns.py         ← Singleton · Observer · Adapter · Flyweight
├── services/
│   └── athlete_service.py         ← ISP · DIP · Higher-Order Functions
├── api/
│   ├── app.py                     ← Application factory (wiring / DI)
│   └── routes.py                  ← RESTful endpoints + CRUD + auth
├── utils/
│   └── auth.py                    ← Token-based auth decorators 
└── test_project.py            ← 38 unit tests (all pass)
```

---

## SOLID Principles Applied

| Principle | Where | How |
|-----------|-------|-----|
| **SRP** | `models/athlete.py`, `models/performance.py` | Each class has exactly one responsibility |
| **OCP** | `FootballPlayer`, `BasketballPlayer` | Extend `Athlete` without modifying it |
| **LSP** | All athlete sub-classes | Pass a `FootballPlayer` anywhere an `Athlete` is expected |
| **ISP** | `services/athlete_service.py` | `IAthleteReader`, `IAthleteWriter`, `IPerformanceLogger` — clients depend only on what they use |
| **DIP** | `AthleteService.__init__` | Receives `DatabaseManager` and `EventBus` via constructor (never instantiates them) |

---

## Design Patterns

### 1. Singleton — `DatabaseManager`
Single shared in-memory store. Thread-safe via double-checked locking.
```python
db1 = DatabaseManager()
db2 = DatabaseManager()
assert db1 is db2   # True
```

### 2. Observer — `EventBus`
Pub/sub: services publish events (`athlete_created`, `performance_recorded`).
`AuditLogObserver` and `PerformanceAlertObserver` react automatically.
```python
bus.subscribe("athlete_created", audit.on_athlete_created)
bus.publish("athlete_created", {"id": 1, "name": "Salah"})
```

### 3. Adapter — `ExternalDataAdapter`
Normalises third-party payloads (FIFA, NBA APIs) into the internal format.
```python
internal = ExternalDataAdapter.from_fifa_api(raw_fifa_json)
```

### 4. Flyweight — `SportConfigFlyweight`
Shares immutable sport configuration objects. Thousands of athletes reference
the same `SportConfig` instance rather than duplicating data.
```python
cfg1 = SportConfigFlyweight.get("Football")
cfg2 = SportConfigFlyweight.get("Football")
assert cfg1 is cfg2   # True — same object
```

---

## Higher-Order Functions

All in `services/athlete_service.py`:

```python
# filter_athletes — HOF predicate
young = service.filter_athletes(lambda a: a.age < 25)

# map_athletes — HOF transform
names = service.map_athletes(lambda a: a.name)

# aggregate_athletes — HOF reduce
total_age = service.aggregate_athletes(lambda acc, a: acc + a.age, 0)

# process_pipeline — compose arbitrary steps
result = service.process_pipeline(
    lambda athletes: filter(lambda a: a.sport == "Football", athletes),
    lambda athletes: map(lambda a: a.to_dict(), athletes),
    list,
)

# build_report — inject formatters at call-time
report = service.build_report(athlete_id, [add_summary, add_grade])
```

---

## Runtime Attribute Injection

```python
athlete = Athlete(...)
athlete.inject_stat("aces", 12)          # new attribute added at runtime
athlete.inject_stat("sport_config", {...})
print(athlete.get_stat("aces"))          # 12
print(athlete.to_dict())                 # includes injected attributes
```

---

## REST API

### Authentication
All endpoints require a Bearer token in the `Authorization` header.

| Token | Role |
|-------|------|
| `admin-token-001` | admin |
| `coach-token-002` | coach |
| `analyst-token-003` | analyst |

### Endpoints

| Method | URL | Auth Required | Description |
|--------|-----|---------------|-------------|
| GET | `/athletes` | any | List all athletes |
| GET | `/athletes/<id>` | any | Get one athlete |
| POST | `/athletes` | admin / coach | Create athlete |
| PUT | `/athletes/<id>` | admin / coach | Update athlete |
| DELETE | `/athletes/<id>` | admin only | Delete athlete |
| POST | `/athletes/<id>/performance` | any | Log performance session |
| GET | `/athletes/<id>/report` | any | Performance report + grade |
| GET | `/analytics/pipeline` | any | Filtered HOF pipeline |
| GET | `/analytics/aggregate` | any | Aggregate stats (reduce) |
| POST | `/import/fifa` | admin | Import via Adapter (FIFA) |
| POST | `/import/nba` | admin | Import via Adapter (NBA) |
| GET | `/sports/config` | any | Flyweight sport config |
| GET | `/events/log` | admin | Observer audit + alerts |

### Example Usage

```bash
# Start the server
python main.py

# List athletes
curl http://localhost:5000/athletes \
  -H "Authorization: Bearer admin-token-001"

# Create a football player
curl -X POST http://localhost:5000/athletes \
  -H "Authorization: Bearer admin-token-001" \
  -H "Content-Type: application/json" \
  -d '{"name":"Salah","age":32,"sport":"Football","team":"Liverpool","nationality":"Egyptian"}'

# Log a performance session
curl -X POST http://localhost:5000/athletes/1/performance \
  -H "Authorization: Bearer coach-token-002" \
  -H "Content-Type: application/json" \
  -d '{"metrics":{"speed":90,"stamina":85,"agility":92},"notes":"Pre-match session"}'

# Get performance report
curl http://localhost:5000/athletes/1/report \
  -H "Authorization: Bearer analyst-token-003"

# Import from FIFA API (Adapter demo)
curl -X POST http://localhost:5000/import/fifa \
  -H "Authorization: Bearer admin-token-001" \
  -H "Content-Type: application/json" \
  -d '{"player_name":"Messi","player_age":37,"club":"Inter Miami","country":"Argentina","pos":"Forward"}'

# Flyweight demo
curl "http://localhost:5000/sports/config?sport=Basketball" \
  -H "Authorization: Bearer admin-token-001"

# HOF pipeline with filter
curl "http://localhost:5000/analytics/pipeline?sport=Football&min_age=25" \
  -H "Authorization: Bearer admin-token-001"
```

---

## Running Tests

```bash
cd sports_analytics
python -m unittest tests.test_project -v
# → 38 tests, all PASS
```

---

## Requirements

```
flask
```

Install:
```bash
pip install flask
```
