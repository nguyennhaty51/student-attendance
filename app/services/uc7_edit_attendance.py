from app.errors import NOT_FOUND, NOT_OWNER_SECTION, ServiceError
from app.extensions import db
from app.models import Attendance, AttendanceLog, AttendanceStatus
from app.services.attendance_common import (
    invalid, parse_status, require_reason, run_threshold_checks, to_positive_int,
)

# ======================================================================================
# Phần 1 – Model helper
# ======================================================================================
def change_status(attendance: Attendance, new_status: AttendanceStatus | str, changed_by: int,
                  reason: str) -> AttendanceLog:
    if attendance.session.section.lecturer_id != changed_by:
        raise ServiceError(NOT_OWNER_SECTION, "Bạn không phụ trách lớp học phần này.", 403)
    new_status = parse_status(new_status)
    reason = require_reason(reason)
    if new_status == attendance.status:
        raise invalid("Trạng thái mới trùng trạng thái hiện tại, không có gì để sửa.")

    log = AttendanceLog(
        attendance=attendance, changed_by=changed_by, old_status=attendance.status,
        new_status=new_status, reason=reason)
    attendance.status = new_status
    db.session.add(log)
    return log


# Gắn phương thức vào class Attendance (nếu trong app/models.py chưa có hàm update_status)
Attendance.update_status = change_status


# ======================================================================================
# Phần 2 – Service
# ======================================================================================
class EditAttendanceMixin:
    @staticmethod
    def edit_attendance(lecturer_id: int, attendance_id: int, new_status, reason: str) -> AttendanceLog:
        """UC7 – sửa một bản ghi điểm danh: đổi trạng thái + thêm đúng một dòng AttendanceLog, cùng giao dịch.

        Lỗi: NOT_FOUND, NOT_OWNER_SECTION (QT4), VALIDATION_ERROR (trạng thái sai hoặc không đổi),
        REASON_REQUIRED (QT6). Sau khi lưu, gọi lại kiểm tra ngưỡng vắng của sinh viên đó.
        """
        attendance = db.session.get(Attendance, to_positive_int(attendance_id, "attendance_id"))
        if attendance is None:
            raise ServiceError(NOT_FOUND, "Không tìm thấy bản ghi điểm danh.", 404)
        student_id = attendance.student_id
        section_id = attendance.session.section_id

        try:
            log = attendance.update_status(new_status, lecturer_id, reason)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        run_threshold_checks(section_id, [student_id])
        return log