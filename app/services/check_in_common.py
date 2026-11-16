import enum
from datetime import datetime, timezone

CODE_LENGTH = 6            # PIN 6 chữ số
DEFAULT_CODE_MINUTES = 5   # thời hạn mã mặc định (UC6)
MAX_CODE_MINUTES = 30      # chặn giảng viên đặt hạn quá dài

MAX_FAILED_ATTEMPTS = 5     # NFR11: số lần nhập sai liên tiếp tối đa
LOCK_SECONDS = 5 * 60       # NFR11: thời gian tạm khóa


def utcnow() -> datetime:
    """Giờ UTC dạng naive (khớp cột DateTime không có tzinfo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CheckInResult(str, enum.Enum):
    """Mã kết quả của Student.check_in (UC3)."""
    SUCCESS = "SUCCESS"                      # điểm danh thành công
    WRONG_CODE = "WRONG_CODE"                # sai mã (hoặc phiên đã đóng -> mã đã xóa)
    EXPIRED = "EXPIRED"                      # mã hết hạn
    NOT_IN_CLASS = "NOT_IN_CLASS"            # sinh viên không thuộc lớp (QT3)
    ALREADY_CHECKED_IN = "ALREADY_CHECKED_IN"  # đã điểm danh buổi này (QT1)
    TOO_MANY_ATTEMPTS = "TOO_MANY_ATTEMPTS"  # nhập sai quá nhiều lần, đang bị khóa (NFR11)


class SessionNotFoundError(LookupError):
    """Không có buổi học với id này."""


class NotSessionLecturerError(PermissionError):
    """Giảng viên không phụ trách lớp của buổi học này (QT4)."""
