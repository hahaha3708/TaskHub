"""Tất cả error messages được tập trung ở đây để tránh hardcode trong router/service."""

# --- Auth
INVALID_CREDENTIALS = "invalid email or password"
INVALID_TOKEN = "invalid or expired token"
INVALID_TOKEN_TYPE = "invalid token type"
REFRESH_TOKEN_REQUIRED = "refresh token required"
REFRESH_TOKEN_REVOKED = "refresh token has been revoked"
REFRESH_TOKEN_REUSED = "refresh token reuse detected, all sessions revoked"
INACTIVE_USER = "inactive user"
EMAIL_ALREADY_REGISTERED = "email already registered"
REQUIRED_FIELD_CANNOT_BE_NULL = "required field cannot be null"
DATA_CONFLICT = "request conflicts with existing data"

# --- User
USER_NOT_FOUND = "user not found"
CANNOT_DELETE_SELF = "cannot delete your own account"
CANNOT_DEMOTE_LAST_ADMIN = "cannot demote or delete the last active admin"
MEMBER_CANNOT_MANAGE_USERS = "only administrators can manage users"
OLD_PASSWORD_INCORRECT = "old password is incorrect"

# --- Workspace
WORKSPACE_NOT_FOUND = "workspace not found"
WORKSPACE_ACCESS_DENIED = "you do not have access to this workspace"
WORKSPACE_OWNER_ONLY = "only the workspace owner can perform this action"
WORKSPACE_MEMBER_ALREADY_EXISTS = "user is already a member of this workspace"
WORKSPACE_MEMBER_NOT_FOUND = "workspace member not found"
CANNOT_REMOVE_WORKSPACE_OWNER = "cannot remove the workspace owner"
CANNOT_ASSIGN_WORKSPACE_OWNER = "workspace owner role cannot be assigned to a member"
WORKSPACE_OWNER_ROLE_IMMUTABLE = "workspace owner's role cannot be changed"
WORKSPACE_USER_NOT_FOUND = "active user not found"

# --- Project
PROJECT_NOT_FOUND = "project not found"
PROJECT_ARCHIVED = "project is archived and cannot be modified"

# --- Task
TASK_NOT_FOUND = "task not found"
ASSIGNEE_NOT_IN_WORKSPACE = "assignee must be a member of the workspace"
DUE_DATE_IN_PAST = "due_date cannot be in the past"

# --- Label
LABEL_NOT_FOUND = "label not found"
LABEL_NOT_IN_PROJECT = "label does not belong to this project"
LABEL_ALREADY_ATTACHED = "label is already attached to this task"
LABEL_NOT_ATTACHED = "label is not attached to this task"

# --- Comment
COMMENT_NOT_FOUND = "comment not found"
COMMENT_EDIT_FORBIDDEN = (
    "only the comment author, workspace owner, or admin can modify this comment"
)

# --- Generic
NOT_FOUND = "resource not found"
FORBIDDEN = "you do not have permission to perform this action"
