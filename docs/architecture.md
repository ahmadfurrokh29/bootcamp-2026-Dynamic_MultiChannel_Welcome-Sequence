# Architecture

## Overview

The system follows a simple producer-consumer pattern. The FastAPI backend acts as the producer — it creates scheduled message records in SQLite when a user signs up. A background daemon thread acts as the consumer — it polls the database every few seconds and sends any messages that are due.

```
┌─────────────┐       POST /signup       ┌───────────────┐
│  Streamlit  │ ────────────────────────► │   FastAPI     │
│  Frontend   │                           │   Backend     │
│             │ ◄──── SignupResponse ───── │               │
└─────────────┘                           └──────┬────────┘
                                                 │ writes 3 rows
                                                 ▼
                                          ┌───────────────┐
                                          │   SQLite DB   │
                                          │ (message_     │
                                          │  schedules)   │
                                          └──────┬────────┘
                                                 │ polls every N seconds
                                                 ▼
                                          ┌───────────────┐
                                          │  Background   │
                                          │   Poller      │
                                          │  (Thread)     │
                                          └──────┬────────┘
                                                 │
                              ┌──────────────────┼──────────────────┐
                              ▼                  ▼                  ▼
                        send_email()         send_sms()        log drift
                        (mock)               (mock)
```

---

## Components

### `src/config.py`
Reads all configuration from environment variables with sensible defaults. This allows the same codebase to run locally with short delays (60s, 120s) and in production with real delays (24h, 48h).

### `src/database.py`
- Creates a SQLAlchemy engine pointing to the SQLite file
- Provides `SessionLocal` for creating DB sessions
- `init_db()` runs `Base.metadata.create_all()` on startup to create tables if they don't exist
- `get_db()` is a FastAPI dependency that yields a session and closes it after the request

### `src/models.py`

**User**
| Column     | Type     | Notes                        |
|------------|----------|------------------------------|
| id         | Integer  | Primary key                  |
| name       | String   |                              |
| email      | String   | Unique                       |
| phone      | String   |                              |
| created_at | DateTime | Auto-set on insert           |

**MessageSchedule**
| Column       | Type     | Notes                                      |
|--------------|----------|--------------------------------------------|
| id           | Integer  | Primary key                                |
| user_id      | Integer  | Foreign key → users.id (cascade delete)   |
| message_type | String   | `welcome`, `sms_followup`, `final_tips`   |
| channel      | String   | `email` or `sms`                          |
| send_at      | DateTime | When the message should be sent            |
| status       | String   | `pending` or `sent`                        |
| sent_at      | DateTime | Actual time it was sent (nullable)         |
| created_at   | DateTime | Auto-set on insert                         |

### `src/schemas.py`
Pydantic v2 schemas for request validation (`SignupRequest`) and response serialization (`SignupResponse`, `ScheduledMessageOut`). Uses `model_config = {"from_attributes": True}` to read from ORM objects.

### `src/senders.py`
Mock senders only — no real email or SMS provider is used. Both `send_email()` and `send_sms()` log a formatted message to:
- The console (stdout)
- A rotating log file at `LOG_FILE` (default: `logs/messages.log`)

### `src/scheduler.py`
The core of the system.

`process_due_messages(db)`:
1. Queries all `MessageSchedule` rows where `status == "pending"` and `send_at <= now`
2. For each due message, calls the appropriate sender
3. Records `sent_at` (actual send time) and logs the drift (`sent_at - send_at`)
4. Updates `status = "sent"` and commits

`run_poller()`:
- Runs in an infinite loop inside a daemon thread
- Opens a fresh DB session each iteration
- Calls `process_due_messages()` then sleeps for `POLL_INTERVAL` seconds

### `src/main.py`
FastAPI application with:
- **Lifespan context manager** — calls `init_db()` and starts the poller thread on startup
- **`POST /signup`** — creates User + 3 MessageSchedule rows
- **`GET /users`** — returns all users
- **`GET /schedules`** — returns all schedules including `sent_at` for drift calculation
- **`DELETE /users/{user_id}`** — deletes user and cascades to their schedules
- **`POST /simulate-crash/{message_id}`** — triggers failure mode demo

### `streamlit_app.py`
Three-page Streamlit app with `st.session_state` as a simple router:

| Page        | Description                                                      |
|-------------|------------------------------------------------------------------|
| `signup`    | Form → POST /signup → redirect to live feed                     |
| `live`      | Shows email card instantly, SMS and tips with countdown timers  |
| `schedules` | Table of users with delete buttons, expanders per schedule with drift metrics |

The live feed page uses `time.sleep(1); st.rerun()` to update countdown timers every second.

---

## Startup & Recovery Flow

```
Process starts
      │
      ├─ init_db()          → creates tables if not exist
      │
      ├─ run_poller()       → daemon thread starts
      │       │
      │       └─ first poll → picks up any pending messages from previous run
      │                        (this is the restart recovery mechanism)
      │
      └─ FastAPI ready      → accepts HTTP requests
```

The database is the single source of truth. There is no in-memory state for the scheduler — every poll reads directly from SQLite. This means the system recovers automatically from crashes, reboots, or restarts.

---

## Drift

Drift is the delay between when a message was *scheduled* to be sent and when it was *actually* sent.

```
drift = sent_at - send_at
```

Sources of drift:
- `POLL_INTERVAL` — a message can be late by up to `POLL_INTERVAL` seconds if it becomes due just after a poll
- Process downtime — if the process was down when a message was due, it will be sent on the next poll after restart

Drift is logged to the log file and displayed as a metric on the Streamlit schedules page.

---

## Failure Mode: Duplicate Send

See [`failure-demo.md`](failure-demo.md) for the full walkthrough.

**Root cause:** The poller sends the message and then updates `status = "sent"`. If the process crashes between these two steps, the message remains `pending` in the database. On the next restart, the poller will find it as pending and send it again — a duplicate.

**Mitigation in production:** Use a database transaction that wraps the send attempt, or implement an idempotency key on the receiver side.
