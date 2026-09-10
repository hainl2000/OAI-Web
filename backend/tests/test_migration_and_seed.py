from alembic import command
from sqlalchemy import inspect, select, text

from app.db import engine
from app.models import User
from app.seed import seed_admin
from tests.conftest import ADMIN_PASSWORD, alembic_config

EXPECTED_TABLES = {
    "users",
    "competitions",
    "registrations",
    "competition_ground_truth",
    "ground_truth_rows",
    "submissions",
}


def test_migration_creates_all_tables():
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES <= tables


def test_migration_downgrade_and_upgrade_roundtrip():
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    assert not (EXPECTED_TABLES & set(inspect(engine).get_table_names()))
    command.upgrade(cfg, "head")
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0001"


def test_seed_admin_is_idempotent_and_hashes_password(db_session):
    first = seed_admin(db_session)
    second = seed_admin(db_session)
    assert first.id == second.id
    admins = db_session.scalars(select(User).where(User.role == "admin")).all()
    assert len(admins) == 1
    assert admins[0].username == "admin"
    assert admins[0].email is None
    assert ADMIN_PASSWORD not in admins[0].password_hash
    assert admins[0].password_hash.startswith("$2")


def test_app_startup_seeds_admin(client, db_session):
    admins = db_session.scalars(select(User).where(User.username == "admin")).all()
    assert len(admins) == 1
