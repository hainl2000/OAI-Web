from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import ApiError
from app.models import ROLE_ADMIN, ROLE_CANDIDATE, User
from app.security import decode_access_token

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get(get_settings().cookie_name)
    if not token:
        raise ApiError(401, "unauthenticated", "Bạn cần đăng nhập.")
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise ApiError(401, "invalid_session", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise ApiError(401, "invalid_session", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(401, "invalid_session", "Tài khoản không còn tồn tại.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != ROLE_ADMIN:
        raise ApiError(403, "forbidden", "Chỉ quản trị viên mới được thực hiện thao tác này.")
    return user


def require_candidate(user: CurrentUser) -> User:
    if user.role != ROLE_CANDIDATE:
        raise ApiError(403, "forbidden", "Chỉ thí sinh mới được thực hiện thao tác này.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
CandidateUser = Annotated[User, Depends(require_candidate)]
