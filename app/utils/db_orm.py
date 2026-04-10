import os
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Optional

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, Float, String, create_engine, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .template import load_templates_as_env_vars

load_dotenv()


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    sla_no_of_hours: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    log: Mapped[Optional[str]] = mapped_column(String)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")  # "open" or "resolved"
    notified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    solution: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=False, server_default=func.now())
    # created_by: Mapped[Optional[str]] = mapped_column(String(255))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    is_human: Mapped[bool] = mapped_column(Boolean, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    images_json: Mapped[Optional[str]] = mapped_column(String)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=False, server_default=func.now())


def _ensure_sqlite_dir(db_url: str) -> str:
    """For sqlite URLs, ensure the parent directory exists before connecting."""
    if not db_url.startswith("sqlite"):
        return db_url
    # Skip in-memory DBs
    if db_url.endswith(":memory:"):
        return db_url

    # sqlite:///relative/path.db or sqlite:////absolute/path.db
    prefix = "sqlite:///"
    path = db_url[len(prefix):] if db_url.startswith(prefix) else db_url
    # On Windows an absolute path may start with /C:/... after sqlite:////
    if path.startswith("/") and ":" in path[:4]:
        path = path[1:]

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    return db_url


@lru_cache()
def get_engine(connection_url: str = None) -> Engine:
    if connection_url is None:
        default_path = os.path.join(os.getcwd(), "data", "incidents.db")
        os.makedirs(os.path.dirname(default_path), exist_ok=True)
        connection_url = os.getenv("DATABASE_URL", f"sqlite:///{default_path}")

    connection_url = _ensure_sqlite_dir(connection_url)
    return create_engine(connection_url)


def get_session(engine: Engine = get_engine()) -> Session:
    return Session(engine)


def create_all_tables(engine: Engine = get_engine()) -> None:
    Base.metadata.create_all(engine)


def init_db():
    data_dir = "./data/"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    create_all_tables()
    load_templates_as_env_vars()
