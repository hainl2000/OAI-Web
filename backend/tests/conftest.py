import os
from pathlib import Path

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://localhost:5432/olympicai_test"
)
# Must be set before the app (and its cached settings / engine) is imported.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", "test-secret-key-that-is-at-least-32-bytes-long")
os.environ.setdefault("COOKIE_SECURE", "false")

import psycopg  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
ADMIN_PASSWORD = "admin123456"

TABLES = [
    "submissions",
    "ground_truth_rows",
    "competition_ground_truth",
    "registrations",
    "competitions",
    "users",
]


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def _ensure_database_exists() -> None:
    url = make_url(TEST_DATABASE_URL)
    admin_dsn = (
        f"host={url.host or 'localhost'} port={url.port or 5432} dbname=postgres"
        + (f" user={url.username}" if url.username else "")
        + (f" password={url.password}" if url.password else "")
    )
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (url.database,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{url.database}"')


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    _ensure_database_exists()
    command.upgrade(alembic_config(), "head")
    yield


@pytest.fixture(autouse=True)
def clean_database(migrated_database):
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_client():
    with TestClient(app) as c:
        response = c.post(
            "/api/v1/auth/login", json={"identifier": "admin", "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, response.text
        yield c


@pytest.fixture
def candidate_factory():
    clients: list[TestClient] = []

    def make(name: str = "Nguyễn Văn A", email: str | None = None, password: str = "password123"):
        email = email or f"user{len(clients) + 1}@example.com"
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        response = c.post(
            "/api/v1/auth/signup", json={"name": name, "email": email, "password": password}
        )
        assert response.status_code == 201, response.text
        c.user = response.json()  # type: ignore[attr-defined]
        return c

    yield make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def candidate_client(candidate_factory):
    return candidate_factory()
