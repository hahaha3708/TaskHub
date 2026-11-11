# --- Task fields
TITLE_MIN_LENGTH = 1
TITLE_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 1000

TASK_NOT_FOUND = "Task not found"
TITLE_CANNOT_BE_NULL = "title cannot be null"
STATUS_CANNOT_BE_NULL = "status cannot be null"
PRIORITY_CANNOT_BE_NULL = "priority cannot be null"

# --- Password (bcrypt limits)
# bcrypt chỉ xử lý 72 byte đầu tiên của mật khẩu (theo spec).
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72

# --- JWT
JWT_ALGORITHM = "HS256"
# Cho phép các thuật toán khi verify (chỉ một trong settings, liệt kê ra đây để tránh magic string).
JWT_ALGORITHMS = [JWT_ALGORITHM]

# --- Field length constraints (đồng bộ với DB columns)
EMAIL_MAX_LENGTH = 255
FULL_NAME_MIN_LENGTH = 1
FULL_NAME_MAX_LENGTH = 255
