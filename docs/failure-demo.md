# Failure Mode Demo: Duplicate Send on Restart

## What is this failure mode?

When the background poller sends a message, it performs two separate steps:
1. Send the message (email or SMS)
2. Update `status = "sent"` in the database

If the process crashes or is killed **between step 1 and step 2**, the message has been sent but the database still shows `status = "pending"`. On the next restart, the poller will find the message as pending and send it **again** — causing a duplicate.

This is a classic at-least-once delivery problem in distributed systems.

---

## How to reproduce

There are two ways to trigger this demo — via the Streamlit UI or via the API directly.

---

### Option A — Streamlit UI (Recommended)

**Step 1 — Start both servers**

```powershell
# Backend (PowerShell)
$env:SMS_DELAY="60"; $env:TIP_DELAY="120"; $env:POLL_INTERVAL="5"; $env:DATABASE_URL="welcome_sequence.db"; $env:LOG_FILE="logs/messages.log"; python -m uvicorn src.main:app --reload

# Frontend (separate terminal)
python -m streamlit run streamlit_app.py
```

**Step 2 — Sign up a new user**

Open `http://localhost:8501` → fill in name, email, phone → click Sign Up.

**Step 3 — Wait on the live feed page**

Watch the welcome email turn green immediately. Wait 60 seconds for the SMS to turn green too. At this point `final_tips` is still pending.

**Step 4 — Go to the Schedules page**

Click "View all schedules". Scroll to the bottom — you will see the **Failure Mode Demo** section.

**Step 5 — Select a pending message and click Simulate Crash**

Select `final_tips` from the dropdown and click **💥 Simulate Crash**.

You will see a red error message:
> "Crash simulated! Message ID X was sent but status is still pending..."

This means the SMS was sent (check `logs/messages.log`) but the database still shows `pending`.

**Step 6 — Restart the backend**

Stop the backend (`Ctrl+C` in its terminal) and start it again with the same command from Step 1.

**Step 7 — Observe the duplicate in the log**

Open `logs/messages.log` — the same `final_tips` message appears **twice**:

```
20:08:24 | SMS SENT | Type: final_tips      ← first send (before crash)
20:08:24 | CRASH SIMULATED — status NOT updated
20:09:20 | Scheduler started — recovering pending messages from DB
20:09:50 | SMS SENT | Type: final_tips      ← duplicate send (after restart)
```

---

### Option B — API directly

**Step 1 — Sign up a new user**

```bash
curl -X POST http://localhost:8000/signup \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com", "phone": "03001234567"}'
```

**Step 2 — Find a pending message ID**

```bash
curl http://localhost:8000/schedules
```

Note the `id` of any message with `"status": "pending"`.

**Step 3 — Trigger the crash**

```bash
curl -X POST http://localhost:8000/simulate-crash/{message_id}
```

**Step 4 — Restart backend and check logs for duplicate**

```bash
# Ctrl+C, then restart
python -m uvicorn src.main:app --reload
```

---

## Timeline

```
T=0   Poller finds message (status=pending, send_at <= now)
T=1   send_sms() called → message logged as sent
T=2   *** CRASH *** (SystemExit raised, status NOT updated in DB)
T=3   Process restarts
T=4   Poller runs → finds same message still pending
T=5   send_sms() called AGAIN → duplicate send
T=6   status updated to "sent"
```

---

## Real-world impact

In production with real Twilio SMS or Gmail:
- The user would receive the same SMS or email twice
- This can cause user confusion and erode trust
- For billing-related or time-sensitive messages, duplicates can have serious consequences

---

## How to prevent it in production

| Strategy | Description |
|----------|-------------|
| **Idempotency keys** | Assign a unique key per message; the SMS/email provider ignores duplicates with the same key |
| **Two-phase commit** | Update status to `"sending"` before sending, then `"sent"` after; on restart, skip `"sending"` messages or check with the provider |
| **Outbox pattern** | Write the send intent and the status update in a single DB transaction; use a separate relay process to forward from outbox to the actual provider |
| **At-most-once delivery** | Update status to `"sent"` before sending; risk is missed sends instead of duplicate sends |
