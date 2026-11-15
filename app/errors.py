"""Lỗi nghiệp vụ dùng chung giữa service và controller. Danh sách mã lỗi: docs/api_contract.md, mục 3.

Đổi/thêm mã lỗi phải sửa đồng thời file này và docs/api_contract.md (mở Pull Request cho TV1).
"""


class ServiceError(Exception):
    """Service ném lỗi này; controller bắt và hiển thị `message` (HTTP status theo bảng mã lỗi)."""

    def __init__(self, code: str, message: str = "", http_status: int = 400):
        super().__init__(message or code)
        self.code = code
        self.message = message or code
        self.http_status = http_status


# Mã lỗi (giữ khớp với docs/api_contract.md mục 3)
AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
AUTH_ACCOUNT_LOCKED = "AUTH_ACCOUNT_LOCKED"
AUTH_WRONG_OLD_PASSWORD = "AUTH_WRONG_OLD_PASSWORD"
FORBIDDEN = "FORBIDDEN"
NOT_FOUND = "NOT_FOUND"
VALIDATION_ERROR = "VALIDATION_ERROR"
NOT_OWNER_SECTION = "NOT_OWNER_SECTION"
NOT_ENROLLED = "NOT_ENROLLED"
DUPLICATE_ATTENDANCE = "DUPLICATE_ATTENDANCE"
REASON_REQUIRED = "REASON_REQUIRED"
CHECKIN_WRONG_CODE = "CHECKIN_WRONG_CODE"
CHECKIN_EXPIRED = "CHECKIN_EXPIRED"
CHECKIN_ALREADY = "CHECKIN_ALREADY"
CHECKIN_TOO_MANY_ATTEMPTS = "CHECKIN_TOO_MANY_ATTEMPTS"
LEAVE_DUPLICATE = "LEAVE_DUPLICATE"
LEAVE_NOT_IN_CLASS = "LEAVE_NOT_IN_CLASS"
LEAVE_ALREADY_DECIDED = "LEAVE_ALREADY_DECIDED"
SESSION_HAS_ATTENDANCE = "SESSION_HAS_ATTENDANCE"
STUDENT_HAS_ATTENDANCE = "STUDENT_HAS_ATTENDANCE"
DUPLICATE_VALUE = "DUPLICATE_VALUE"
