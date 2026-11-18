# --- Task fields
TITLE_MIN_LENGTH = 1
TITLE_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 1000

TASK_NOT_FOUND = "Task not found"
TITLE_CANNOT_BE_NULL = "title cannot be null"
STATUS_CANNOT_BE_NULL = "status cannot be null"
PRIORITY_CANNOT_BE_NULL = "priority cannot be null"

# --- Roles with write permission in a workspace
WORKSPACE_WRITE_ROLES = frozenset({"OWNER", "EDITOR"})

# --- Pagination defaults
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# --- Project fields
PROJECT_NAME_MIN_LENGTH = 1
PROJECT_NAME_MAX_LENGTH = 255
PROJECT_DESCRIPTION_MAX_LENGTH = 1000

# --- Label fields
LABEL_NAME_MIN_LENGTH = 1
LABEL_NAME_MAX_LENGTH = 100
LABEL_COLOR_MAX_LENGTH = 20

# --- Comment fields
COMMENT_CONTENT_MIN_LENGTH = 1
COMMENT_CONTENT_MAX_LENGTH = 5000

# --- Password (bcrypt limits)
# bcrypt chỉ xử lý 72 byte đầu tiên của mật khẩu (theo spec).
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72

# --- JWT
JWT_ALGORITHM = "HS256"
# Giới hạn thuật toán xác minh theo cấu hình, không nhận thuật toán từ token.
JWT_ALGORITHMS = [JWT_ALGORITHM]

# --- Field length constraints (đồng bộ với DB columns)
EMAIL_MAX_LENGTH = 255
FULL_NAME_MIN_LENGTH = 1
FULL_NAME_MAX_LENGTH = 255
