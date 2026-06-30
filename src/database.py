from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.config import DATABASE_URL

# Create the SQLite database engine.
# check_same_thread=False allows the same connection to be used across threads
# (needed because the background poller runs in a separate thread).
engine = create_engine(
    f"sqlite:///{DATABASE_URL}",
    connect_args={"check_same_thread": False},
)

# SessionLocal is a factory — call it to get a new DB session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# All ORM models must inherit from this Base class
class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that provides a DB session per request and closes it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all database tables if they do not already exist."""
    from src import models  # noqa: F401 — import needed so Base knows about the models
    Base.metadata.create_all(bind=engine)
