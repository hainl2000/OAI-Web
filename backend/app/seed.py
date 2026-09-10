"""Idempotent seeding of the built-in admin account."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ROLE_ADMIN, User
from app.security import hash_password


def seed_admin(db: Session) -> User:
    settings = get_settings()
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    if admin is None:
        admin = User(
            name=settings.admin_name,
            username=settings.admin_username,
            email=None,
            password_hash=hash_password(settings.admin_password),
            role=ROLE_ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return admin


if __name__ == "__main__":
    from app.db import SessionLocal

    with SessionLocal() as session:
        user = seed_admin(session)
        print(f"admin ready: id={user.id} username={user.username}")
