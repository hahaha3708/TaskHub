from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.exceptions import (
    ForbiddenException,
    InactiveUserException,
    InvalidTokenException,
)
from app.core.security import decode_token
from app.db.session import get_session
from app.models.enums import TokenType, UserRole
from app.models.user import User
from app.repositories.task import TaskRepository
from app.services.auth import AuthService
from app.services.task import TaskService
from app.services.user import UserService
from app.services.workspace import WorkspaceService

DbSession = Annotated[AsyncSession, Depends(get_session)]


# --- Auth dependencies -------------------------------------------------


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise InvalidTokenException()
    return authorization.split(" ", 1)[1]


async def get_current_user(
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Decode access token → lấy user → kiểm tra active.

    Toàn bộ logic ở một chỗ, KHÔNG copy-paste ở nhiều nơi.
    """
    token = _extract_bearer_token(authorization)
    claims = decode_token(token, TokenType.ACCESS)
    user = await session.get(User, claims["user_id"])
    if user is None:
        raise InvalidTokenException()
    if not user.is_active:
        raise InactiveUserException()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(current_user: CurrentUser) -> User:
    """Chặn member khỏi thao tác admin."""
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException(messages.MEMBER_CANNOT_MANAGE_USERS)
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


# --- Service factories ------------------------------------------------


def get_task_repository(session: DbSession) -> TaskRepository:
    return TaskRepository(session)


def get_task_service(
    repository: Annotated[TaskRepository, Depends(get_task_repository)],
) -> TaskService:
    return TaskService(repository=repository)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_user_service(session: DbSession) -> UserService:
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_workspace_service(session: DbSession) -> WorkspaceService:
    return WorkspaceService(session)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
