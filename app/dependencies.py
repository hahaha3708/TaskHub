from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Path
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import messages
from app.core.constants import WORKSPACE_WRITE_ROLES
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    InactiveUserException,
    InvalidTokenException,
    NotFoundException,
)
from app.core.security import decode_token
from app.db.session import get_session
from app.models.comment import Comment
from app.models.enums import ProjectStatus, TokenType, UserRole, WorkspaceRole
from app.models.label import Label
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.comment import CommentRepository
from app.repositories.label import LabelRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.base import PaginationParams
from app.services.auth import AuthService
from app.services.comment import CommentService
from app.services.label import LabelService
from app.services.project import ProjectService
from app.services.task import TaskService
from app.services.user import UserService
from app.services.workspace import WorkspaceService

DbSession = Annotated[AsyncSession, Depends(get_session)]

# --- Path aliases with validation --------------------------------------
WorkspaceId = Annotated[int, Path(gt=0, description="Workspace ID")]
ProjectId = Annotated[int, Path(gt=0, description="Project ID")]
TaskId = Annotated[int, Path(gt=0, description="Task ID")]
LabelId = Annotated[int, Path(gt=0, description="Label ID")]
CommentId = Annotated[int, Path(gt=0, description="Comment ID")]
UserId = Annotated[int, Path(gt=0, description="User ID")]

# --- Pagination dependency ---------------------------------------------
PaginationDep = Annotated[PaginationParams, Depends()]


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


# --- Access contexts & policies ----------------------------------------


@dataclass(slots=True)
class WorkspaceContext:
    workspace: Workspace
    role: WorkspaceRole
    is_admin: bool

    def check_can_read(self) -> None:
        pass

    def check_can_write(self) -> None:
        if not self.is_admin and self.role not in WORKSPACE_WRITE_ROLES:
            raise ForbiddenException(messages.FORBIDDEN)

    def check_owner(self) -> None:
        if not self.is_admin and self.role != WorkspaceRole.OWNER:
            raise ForbiddenException(messages.WORKSPACE_OWNER_ONLY)


@dataclass(slots=True)
class ProjectContext:
    project: Project
    workspace: Workspace
    role: WorkspaceRole
    is_admin: bool

    def check_can_read(self) -> None:
        pass

    def check_can_write(self) -> None:
        if not self.is_admin and self.role not in WORKSPACE_WRITE_ROLES:
            raise ForbiddenException(messages.FORBIDDEN)
        if self.project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(messages.PROJECT_ARCHIVED)

    def check_can_change_archive(self) -> None:
        if not self.is_admin and self.role not in WORKSPACE_WRITE_ROLES:
            raise ForbiddenException(messages.FORBIDDEN)


@dataclass(slots=True)
class TaskContext:
    task: Task
    project: Project
    workspace: Workspace
    role: WorkspaceRole
    is_admin: bool

    def check_can_read(self) -> None:
        pass

    def check_can_write(self) -> None:
        if not self.is_admin and self.role not in WORKSPACE_WRITE_ROLES:
            raise ForbiddenException(messages.FORBIDDEN)
        if self.project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(messages.PROJECT_ARCHIVED)


@dataclass(slots=True)
class CommentContext:
    comment: Comment
    task: Task
    project: Project
    workspace: Workspace
    role: WorkspaceRole
    is_admin: bool

    def check_can_read(self) -> None:
        pass

    def check_can_delete_or_edit(self, user_id: int) -> None:
        can_manage = (
            self.is_admin
            or self.role == WorkspaceRole.OWNER
            or self.comment.author_id == user_id
        )
        if not can_manage:
            raise ForbiddenException(messages.COMMENT_EDIT_FORBIDDEN)
        if self.project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(messages.PROJECT_ARCHIVED)


@dataclass(slots=True)
class LabelContext:
    label: Label
    project: Project
    workspace: Workspace
    role: WorkspaceRole
    is_admin: bool

    def check_can_read(self) -> None:
        pass

    def check_can_write(self) -> None:
        if not self.is_admin and self.role not in WORKSPACE_WRITE_ROLES:
            raise ForbiddenException(messages.FORBIDDEN)
        if self.project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(messages.PROJECT_ARCHIVED)


def _resolve_membership(
    workspace: Workspace,
    member_role: WorkspaceRole | None,
    current_user: User,
) -> tuple[WorkspaceRole, bool]:
    is_admin = current_user.role == UserRole.ADMIN
    is_owner = (
        workspace.owner_id == current_user.id or member_role == WorkspaceRole.OWNER
    )
    if not is_admin and not is_owner and member_role is None:
        raise ForbiddenException(messages.WORKSPACE_ACCESS_DENIED)
    effective_role = WorkspaceRole.OWNER if (is_admin or is_owner) else member_role
    return effective_role, is_admin  # type: ignore[return-value]


# --- Context loaders (Dependencies) ------------------------------------


async def get_workspace_context(
    workspace_id: WorkspaceId,
    current_user: CurrentUser,
    session: DbSession,
) -> WorkspaceContext:
    statement = (
        select(Workspace, WorkspaceMember.role)
        .outerjoin(
            WorkspaceMember,
            and_(
                WorkspaceMember.workspace_id == Workspace.id,
                WorkspaceMember.user_id == current_user.id,
            ),
        )
        .where(Workspace.id == workspace_id)
    )
    row = (await session.execute(statement)).first()
    if row is None:
        raise NotFoundException(messages.WORKSPACE_NOT_FOUND)
    workspace, member_role = row
    effective_role, is_admin = _resolve_membership(workspace, member_role, current_user)
    return WorkspaceContext(
        workspace=workspace,
        role=effective_role,
        is_admin=is_admin,
    )


async def get_project_context(
    project_id: ProjectId,
    current_user: CurrentUser,
    session: DbSession,
) -> ProjectContext:
    statement = (
        select(Project, Workspace, WorkspaceMember.role)
        .join(Workspace, Project.workspace_id == Workspace.id)
        .outerjoin(
            WorkspaceMember,
            and_(
                WorkspaceMember.workspace_id == Workspace.id,
                WorkspaceMember.user_id == current_user.id,
            ),
        )
        .where(Project.id == project_id)
    )
    row = (await session.execute(statement)).first()
    if row is None:
        raise NotFoundException(messages.PROJECT_NOT_FOUND)
    project, workspace, member_role = row
    effective_role, is_admin = _resolve_membership(workspace, member_role, current_user)
    return ProjectContext(
        project=project,
        workspace=workspace,
        role=effective_role,
        is_admin=is_admin,
    )


async def get_task_context(
    task_id: TaskId,
    current_user: CurrentUser,
    session: DbSession,
) -> TaskContext:
    statement = (
        select(Task, Project, Workspace, WorkspaceMember.role)
        .join(Project, Task.project_id == Project.id)
        .join(Workspace, Project.workspace_id == Workspace.id)
        .outerjoin(
            WorkspaceMember,
            and_(
                WorkspaceMember.workspace_id == Workspace.id,
                WorkspaceMember.user_id == current_user.id,
            ),
        )
        .options(selectinload(Task.labels))
        .where(Task.id == task_id)
    )
    row = (await session.execute(statement)).first()
    if row is None:
        raise NotFoundException(messages.TASK_NOT_FOUND)
    task, project, workspace, member_role = row
    effective_role, is_admin = _resolve_membership(workspace, member_role, current_user)
    return TaskContext(
        task=task,
        project=project,
        workspace=workspace,
        role=effective_role,
        is_admin=is_admin,
    )


async def get_comment_context(
    comment_id: CommentId,
    current_user: CurrentUser,
    session: DbSession,
) -> CommentContext:
    statement = (
        select(Comment, Task, Project, Workspace, WorkspaceMember.role)
        .join(Task, Comment.task_id == Task.id)
        .join(Project, Task.project_id == Project.id)
        .join(Workspace, Project.workspace_id == Workspace.id)
        .outerjoin(
            WorkspaceMember,
            and_(
                WorkspaceMember.workspace_id == Workspace.id,
                WorkspaceMember.user_id == current_user.id,
            ),
        )
        .where(Comment.id == comment_id)
    )
    row = (await session.execute(statement)).first()
    if row is None:
        raise NotFoundException(messages.COMMENT_NOT_FOUND)
    comment, task, project, workspace, member_role = row
    effective_role, is_admin = _resolve_membership(workspace, member_role, current_user)
    return CommentContext(
        comment=comment,
        task=task,
        project=project,
        workspace=workspace,
        role=effective_role,
        is_admin=is_admin,
    )


async def get_label_context(
    label_id: LabelId,
    current_user: CurrentUser,
    session: DbSession,
) -> LabelContext:
    statement = (
        select(Label, Project, Workspace, WorkspaceMember.role)
        .join(Project, Label.project_id == Project.id)
        .join(Workspace, Project.workspace_id == Workspace.id)
        .outerjoin(
            WorkspaceMember,
            and_(
                WorkspaceMember.workspace_id == Workspace.id,
                WorkspaceMember.user_id == current_user.id,
            ),
        )
        .where(Label.id == label_id)
    )
    row = (await session.execute(statement)).first()
    if row is None:
        raise NotFoundException(messages.LABEL_NOT_FOUND)
    label, project, workspace, member_role = row
    effective_role, is_admin = _resolve_membership(workspace, member_role, current_user)
    return LabelContext(
        label=label,
        project=project,
        workspace=workspace,
        role=effective_role,
        is_admin=is_admin,
    )


WorkspaceContextDep = Annotated[WorkspaceContext, Depends(get_workspace_context)]
ProjectContextDep = Annotated[ProjectContext, Depends(get_project_context)]
TaskContextDep = Annotated[TaskContext, Depends(get_task_context)]
CommentContextDep = Annotated[CommentContext, Depends(get_comment_context)]
LabelContextDep = Annotated[LabelContext, Depends(get_label_context)]


# --- Service & Repo factories ------------------------------------------


def get_task_repository(session: DbSession) -> TaskRepository:
    return TaskRepository(session)


def get_task_service(session: DbSession) -> TaskService:
    return TaskService(session=session)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def get_project_repository(session: DbSession) -> ProjectRepository:
    return ProjectRepository(session)


def get_project_service(session: DbSession) -> ProjectService:
    return ProjectService(session=session)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


def get_label_repository(session: DbSession) -> LabelRepository:
    return LabelRepository(session)


def get_label_service(session: DbSession) -> LabelService:
    return LabelService(session=session)


LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]


def get_comment_repository(session: DbSession) -> CommentRepository:
    return CommentRepository(session)


def get_comment_service(session: DbSession) -> CommentService:
    return CommentService(session=session)


CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_user_service(session: DbSession) -> UserService:
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_workspace_service(session: DbSession) -> WorkspaceService:
    return WorkspaceService(session)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
