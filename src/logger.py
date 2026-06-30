import logging
import os
from src.config import LOG_FILE

# Create the logs/ directory if it does not exist yet
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# One shared logger used across the entire application
logger = logging.getLogger("welcome_sequence")
logger.setLevel(logging.INFO)

# Format: "2026-06-29 19:00:00 | MESSAGE"
_fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# File handler — writes logs to disk (persistent)
_fh = logging.FileHandler(LOG_FILE)
_fh.setFormatter(_fmt)

# Console handler — prints logs to terminal (visible while running)
_ch = logging.StreamHandler()
_ch.setFormatter(_fmt)

logger.addHandler(_fh)
logger.addHandler(_ch)
