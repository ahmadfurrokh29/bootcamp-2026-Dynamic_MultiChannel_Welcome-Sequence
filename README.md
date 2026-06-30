# Dynamic Multi-Channel Welcome Sequence

A Python internship project that demonstrates a production-grade multi-channel welcome messaging system. When a user signs up, the system automatically sends a welcome email immediately, an SMS follow-up after a configurable delay, and a final tips message after another delay — all persisted in SQLite so the schedule survives process restarts.

---

## Features

- **Multi-channel messaging** — welcome email, SMS follow-up, and final tips
- **Persistent scheduling** — SQLite-backed scheduler; pending messages are recovered on restart
- **Drift tracking** — logs and displays how late each message was sent vs. its scheduled time
- **Failure mode demo** — `/simulate-crash` endpoint shows what happens when a process dies after sending but before marking the message as sent (duplicate send on restart)
- **Mock senders** — no real email or SMS provider; all messages are logged to console and a log file
- **Streamlit UI** — signup form, live countdown feed, and schedules overview with drift metrics
- **GitHub Actions CI** — runs pytest on every push and pull request

---

## Tech Stack

| Layer       | Technology                         |
|-------------|------------------------------------|
| Backend     | FastAPI + Uvicorn                  |
| Database    | SQLite via SQLAlchemy ORM (v2)     |
| Scheduler   | Python `threading.Thread` (daemon) |
| Frontend    | Streamlit                          |
| Validation  | Pydantic v2                        |
| Testing     | pytest + httpx                     |
| CI          | GitHub Actions                     |

---

## Project Structure

```
├── src/
│   ├── config.py           # Environment variable configuration
│   ├── database.py         # SQLAlchemy engine, session, Base, init_db
│   ├── models.py           # User and MessageSchedule ORM models
│   ├── schemas.py          # Pydantic v2 request/response schemas
│   ├── senders.py          # Mock email and SMS senders (console + file log)
│   ├── scheduler.py        # Background poller, drift logging, crash simulation
│   └── main.py             # FastAPI app, lifespan, all API endpoints
├── tests/
│   ├── test_signup.py      # Signup endpoint tests
│   └── test_scheduler.py   # Scheduler logic tests
├── docs/
│   ├── architecture.md     # System design and flow
│   ├── failure-demo.md     # Failure mode walkthrough
│   └── ai-review-summary.md
├── streamlit_app.py        # Streamlit frontend (3 pages)
├── .env.example            # Environment variable reference
├── requirements.txt
└── .github/workflows/ci.yml
```

---

## Setup & Running

### 1. Clone and install dependencies

```bash
git clone https://github.com/ahmadfurrokh29/bootcamp-2026-Dynamic_MultiChannel_Welcome-Sequence.git
cd bootcamp-2026-Dynamic_MultiChannel_Welcome-Sequence
git checkout ahmad-furrokh/welcome-sequence

pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

| Variable        | Default               | Production        |
|-----------------|-----------------------|-------------------|
| `SMS_DELAY`     | `60` (seconds)        | `86400` (24h)     |
| `TIP_DELAY`     | `120` (seconds)       | `172800` (48h)    |
| `POLL_INTERVAL` | `5` (seconds)         | `5`               |
| `DATABASE_URL`  | `welcome_sequence.db` | your DB path      |
| `LOG_FILE`      | `logs/messages.log`   | your log path     |

### 3. Start the backend

```bash
uvicorn src.main:app --reload
```

Backend runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 4. Start the frontend

```bash
streamlit run streamlit_app.py
```

Frontend runs at `http://localhost:8501`.

---

## API Endpoints

| Method   | Endpoint                       | Description                                     |
|----------|--------------------------------|-------------------------------------------------|
| `POST`   | `/signup`                      | Register a user and schedule 3 messages         |
| `GET`    | `/users`                       | List all registered users                       |
| `GET`    | `/schedules`                   | List all message schedules with drift data      |
| `DELETE` | `/users/{user_id}`             | Delete a user and all their scheduled messages  |
| `POST`   | `/simulate-crash/{message_id}` | Demo failure mode: crash before status update   |

---

## Running Tests

```bash
pytest tests/ -v
```

All 10 tests pass. The CI pipeline runs the same command on every push and pull request.

---

## Message Flow

```
User Signs Up
      │
      ├─► Welcome Email   (sent immediately)
      │
      ├─► SMS Follow-up   (sent after SMS_DELAY seconds)
      │
      └─► Final Tips      (sent after SMS_DELAY + TIP_DELAY seconds)
```

The background poller checks the database every `POLL_INTERVAL` seconds and sends any messages whose `send_at` time has passed. If the process restarts, all pending messages are picked up automatically from the database.

---

## Failure Mode Demo

See [`docs/failure-demo.md`](docs/failure-demo.md) for a step-by-step walkthrough of the duplicate-send failure mode using the `/simulate-crash` endpoint.
