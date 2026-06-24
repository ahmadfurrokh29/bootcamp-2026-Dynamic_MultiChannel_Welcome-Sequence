import logging
import os
from src.config import LOG_FILE

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logger = logging.getLogger("welcome_sequence")
logger.setLevel(logging.INFO)

_fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

_fh = logging.FileHandler(LOG_FILE)
_fh.setFormatter(_fmt)

_ch = logging.StreamHandler()
_ch.setFormatter(_fmt)

logger.addHandler(_fh)
logger.addHandler(_ch)
