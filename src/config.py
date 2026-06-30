import os

# Read configuration from environment variables.
# If a variable is not set, the default value is used.
# For local testing use small delays; for production use large delays.

SMS_DELAY     = int(os.getenv("SMS_DELAY",     86400))  # seconds before SMS is sent  (prod: 24h, test: 60s)
TIP_DELAY     = int(os.getenv("TIP_DELAY",    172800))  # seconds before tips are sent (prod: 48h, test: 120s)
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL",      5)) # how often the scheduler checks the DB (seconds)
DATABASE_URL  = os.getenv("DATABASE_URL", "welcome_sequence.db") # SQLite file path
LOG_FILE      = os.getenv("LOG_FILE",     "logs/messages.log")   # where to write message logs
