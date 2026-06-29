# Failure Mode Demo: Duplicate Send on Restart

## What is this failure mode?

When the background poller sends a message, it performs two separate steps:
1. Send the message (email or SMS)
2. Update `status = "sent"` in the database

If the process crashes or is killed **between step 1 and step 2**, the message has been sent but the database still shows `status = "pending"`. On the next restart, the poller will find the message as pending and send it **again** — causing a duplicate.

This is a classic at-least-once delivery problem in distributed systems.

---

## How to reproduce

### Prerequisites
- Backend running: `uvicorn src.main:app --reload`
- At least one user signed up with a pending message

### Step 1 — Sign up a new user

```bash
curl -X POST http://localhost:8000/signup \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com", "phone": "03001234567"}'
```

Note the message IDs from the response. The welcome email (message ID 1 or similar) is sent immediately. Wait a few seconds for the SMS follow-up to become pending.

### Step 2 — Check pending messages

```bash
curl http://localhost:8000/schedules
```

Find a message with `"status": "pending"` and note its `id`.

### Step 3 — Trigger the simulated crash

```bash
curl -X POST http://localhost:8000/simulate-crash/{message_id}
```

Replace `{message_id}` with the ID of the pending message.

**What happens internally:**
1. The poller finds the message as due
2. `send_sms()` is called — the message is "sent" (logged to console and file)
3. **Before** `status = "sent"` is written to the database — `SystemExit` is raised
4. The API returns `{"detail": "Simulated crash for failure mode demo"}`

### Step 4 — Verify the message is still pending

```bash
curl http://localhost:8000/schedules
```

The message status is still `"pending"` even though the send already happened. Check `logs/messages.log` — you will see the send log entry.

### Step 5 — Restart the backend

Stop and restart the uvicorn process:

```bash
# Ctrl+C to stop, then:
uvicorn src.main:app --reload
```

### Step 6 — Observe the duplicate send

Check the log file:

```bash
cat logs/messages.log
```

You will see the same message sent **twice** — once before the crash and once after the restart recovery. The message now shows `"status": "sent"` in the database.

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
