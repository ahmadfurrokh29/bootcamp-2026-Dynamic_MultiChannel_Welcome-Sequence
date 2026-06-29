# AI Code Review Summary

This document records a self-conducted AI code review of the project, modeled after tools like GitHub Copilot Review and CodeRabbit. Each finding includes the suggestion, the file and line affected, and the action taken.

---

## Review Findings

---

### Finding 1 — Duplicate `_now()` function

**File:** `src/main.py` (line 16) and `src/scheduler.py` (line 13)

**Suggestion:**
The same `_now()` helper is defined in two separate files. If the implementation ever changes (e.g., timezone handling), it must be updated in two places, which is a maintenance risk.

```python
# defined in main.py
def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

# same function also defined in scheduler.py
def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

**Action Taken:** ✅ Fixed
Removed the duplicate definition from `main.py`. The function now lives only in `scheduler.py` and is imported into `main.py`:

```python
from src.scheduler import run_poller, process_due_messages, _now
```

---

### Finding 2 — `datetime.utcnow` is deprecated in Python 3.12+

**File:** `src/models.py` (lines 14, 28)

**Suggestion:**
`datetime.utcnow()` is deprecated since Python 3.12 and will be removed in a future version. Using it as a column default causes deprecation warnings at runtime. The correct replacement is `datetime.now(timezone.utc)`.

```python
# Before — deprecated
created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**Action Taken:** ✅ Fixed
Added a `_utcnow()` helper in `models.py` and used it as the column default:

```python
def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
```

---

### Finding 3 — `/users` and `/schedules` endpoints return raw dicts instead of Pydantic schemas

**File:** `src/main.py` (lines 67–87)

**Suggestion:**
The `/signup` endpoint correctly uses a `response_model` and Pydantic schemas for serialization. But `/users` and `/schedules` manually build Python dicts. This is inconsistent — if a field is added or renamed in the model, the dict must be updated manually and there is no compile-time safety.

```python
# No response_model, no schema validation
@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return [{"id": u.id, "name": u.name, ...} for u in db.query(User).all()]
```

**Action Taken:** ⚠️ Noted, not refactored
The manual dict approach works correctly for this project's scope. Introducing separate `UserOut` and `ScheduleOut` response schemas would be the right fix in a production codebase, but was out of scope for this internship project.

---

### Finding 4 — `except Exception` in the poller swallows all errors silently

**File:** `src/scheduler.py` (line 56)

**Suggestion:**
The poller wraps `process_due_messages()` in a broad `except Exception` block. While this prevents the poller thread from crashing, it also silently swallows errors like DB connection failures or unexpected exceptions. An operator would have no way to know the poller is broken unless they watch the logs closely.

```python
except Exception as exc:
    logger.error(f"Poller error: {exc}")
```

**Action Taken:** ⚠️ Noted, not changed
For a demo project this is acceptable — the poller must not crash the whole app. In production, this should be connected to an alerting system (e.g., Sentry, PagerDuty) so that repeated poller errors trigger an alert.

---

### Finding 5 — `simulate_crash` catches `SystemExit` which is not an `Exception`

**File:** `src/main.py` (line 104)

**Suggestion:**
`SystemExit` inherits from `BaseException`, not `Exception`. Catching it is unusual and could mask real process-exit signals. A custom exception class would be cleaner and more explicit for the failure mode demo.

```python
# Before
raise SystemExit("Simulated crash for failure mode demo")

# Better approach
class SimulatedCrashError(Exception):
    pass

raise SimulatedCrashError("Simulated crash for failure mode demo")
```

**Action Taken:** ⚠️ Noted, not changed
The current approach works for the demo purpose. `SystemExit` communicates the intent clearly (process would have died here), and the endpoint catches it explicitly. Changing it would be a low-priority refactor.

---

### Finding 6 — No phone number validation in `SignupRequest`

**File:** `src/schemas.py`

**Suggestion:**
The `phone` field accepts any string. A user could submit an empty string, letters, or a 100-character value and it would be accepted without error.

```python
class SignupRequest(BaseModel):
    name:  str
    email: EmailStr  # validated
    phone: str       # no validation
```

**Action Taken:** ⚠️ Noted, not changed
Since this project uses mock senders (no real SMS provider), phone validation has no functional impact. In a production system with Twilio or a similar provider, this should use a regex validator or a library like `phonenumbers`.

---

## Summary

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | Duplicate `_now()` function | Medium | ✅ Fixed |
| 2 | `datetime.utcnow` deprecated | Medium | ✅ Fixed |
| 3 | No Pydantic schemas on GET endpoints | Low | ⚠️ Noted |
| 4 | Broad `except Exception` in poller | Low | ⚠️ Noted |
| 5 | `SystemExit` used as control flow | Low | ⚠️ Noted |
| 6 | No phone number validation | Low | ⚠️ Noted |
