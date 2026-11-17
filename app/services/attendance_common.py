from typing import Any, Iterable

from flask import current_app

from app.errors import REASON_REQUIRED, VALIDATION_ERROR, ServiceError
from app.extensions import db
from app.models.enums import AttendanceStatus

MAX_NOTE_LENGTH = 255    # attendances.note
MAX_REASON_LENGTH = 255  # attendance_logs.reason


def invalid(message: str) -> ServiceError:
    return ServiceError(VALIDATION_ERROR, message, 400)


def to_positive_int(value: Any, field: str) -> int:
    """Số nguyên dương (chấp nhận chuỗi số như '12' từ form). bool/float bị từ chối."""
    if isinstance(value, (bool, float)):
        raise invalid(f"{field} không hợp lệ.")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise invalid(f"{field} không hợp lệ.") from None
    if number <= 0:
        raise invalid(f"{field} không hợp lệ.")
    return number


def parse_status(value: Any) -> AttendanceStatus:
    """Nhận enum hoặc tên trạng thái ('PRESENT', 'late'...). Chỉ 4 giá trị hợp lệ."""
    if isinstance(value, AttendanceStatus):
        return value
    if isinstance(value, str):
        try:
            return AttendanceStatus[value.strip().upper()]
        except KeyError:
            pass
    raise invalid("Trạng thái điểm danh không hợp lệ: phải là PRESENT, ABSENT, LATE hoặc EXCUSED.")


def optional_text(value: Any) -> str | None:
    """None hoặc chuỗi đã strip; chuỗi rỗng → None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise invalid("Ghi chú/lý do phải là chuỗi ký tự.")
    return value.strip() or None


def require_reason(value: Any) -> str:
    """QT6 / BR6: sửa điểm danh bắt buộc có lý do (không chỉ toàn khoảng trắng), tối đa 255 ký tự."""
    reason = optional_text(value)
    if reason is None:
        raise ServiceError(REASON_REQUIRED, "Sửa điểm danh phải nhập lý do.", 400)
    if len(reason) > MAX_REASON_LENGTH:
        raise invalid(f"Lý do tối đa {MAX_REASON_LENGTH} ký tự.")
    return reason


def run_threshold_checks(section_id: int, student_ids: Iterable[int]) -> None:
    """Gọi `AttendanceService.check_absence_threshold` (UC15, Issue TV2-3) sau khi đã lưu.

    Hàm đó do TV2-3 viết; nhánh nào chưa có thì bỏ qua để UC5/UC7 chạy độc lập. Lỗi ở bước cảnh báo
    không được làm hỏng điểm danh đã lưu thành công nên chỉ ghi log.
    """
    from app.services.attendance_service import AttendanceService  # tránh import vòng

    checker = getattr(AttendanceService, "check_absence_threshold", None)
    if checker is None:
        return
    for student_id in student_ids:
        try:
            checker(student_id, section_id)
        except Exception:  # noqa: BLE001 - xem docstring
            db.session.rollback()
            current_app.logger.exception(
                "check_absence_threshold lỗi (student_id=%s, section_id=%s)", student_id, section_id)
