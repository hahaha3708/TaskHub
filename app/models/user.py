from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.task import Task
    from app.models.workspace import Workspace, WorkspaceMember


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        default=UserRole.MEMBER,
        server_default=UserRole.MEMBER.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
    )

    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="owner")
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="user",
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(
        foreign_keys="Task.assignee_id",
        back_populates="assignee",
    )
    created_tasks: Mapped[list["Task"]] = relationship(
        foreign_keys="Task.created_by",
        back_populates="creator",
    )
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")
