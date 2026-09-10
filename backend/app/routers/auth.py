from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.errors import ApiError
from app.models import ROLE_ADMIN, ROLE_CANDIDATE, User
from app.schemas import LoginIn, OkOut, SignupIn, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=create_access_token(user.id, user.role),
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.cookie_name, path="/", httponly=True, samesite="lax", secure=settings.cookie_secure
    )


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, response: Response, db: DbSession) -> User:
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise ApiError(409, "email_taken", "Email này đã được đăng ký.")
    user = User(
        name=payload.name,
        email=email,
        username=None,
        password_hash=hash_password(payload.password),
        role=ROLE_CANDIDATE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, user)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: DbSession) -> User:
    identifier = payload.identifier.strip()
    # Admins log in with their username; candidates with their email.
    user = db.scalar(select(User).where(User.username == identifier, User.role == ROLE_ADMIN))
    if user is None:
        user = db.scalar(
            select(User).where(User.email == identifier.lower(), User.role == ROLE_CANDIDATE)
        )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise ApiError(401, "invalid_credentials", "Thông tin đăng nhập không đúng.")
    _set_session_cookie(response, user)
    return user


@router.post("/logout", response_model=OkOut)
def logout(response: Response) -> OkOut:
    _clear_session_cookie(response)
    return OkOut()


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
