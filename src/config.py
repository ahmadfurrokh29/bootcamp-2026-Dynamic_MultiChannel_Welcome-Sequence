import os

SMS_DELAY    = int(os.getenv("SMS_DELAY",    86400))   # 24h prod | 60s test
TIP_DELAY    = int(os.getenv("TIP_DELAY",    172800))  # 48h prod | 120s test
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 5))
DATABASE_URL = os.getenv("DATABASE_URL", "welcome_sequence.db")
LOG_FILE     = os.getenv("LOG_FILE",     "logs/messages.log")
