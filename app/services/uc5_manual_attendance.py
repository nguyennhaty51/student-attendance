import re
from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy.exc import IntegrityError

from app.errors import (
    DUPLICATE_ATTENDANCE, NOT_ENROLLED, NOT_FOUND, NOT_OWNER_SECTION, REASON_REQUIRED, ServiceError,
)
from app.extensions import db
from app.models import (
    Attendance, AttendanceStatus, CheckInMethod, ClassSession, Enrollment, LeaveRequest, LeaveStatus, Student,
)
from app.services.attendance_common import (
    MAX_NOTE_LENGTH, MAX_REASON_LENGTH, invalid, optional_text, parse_status, run_threshold_checks,
    to_positive_int,
)

# Giá trị "không truyền ghi chú" (khác với ghi chú rỗng = xóa ghi chú).
KEEP_NOTE = object()

ACTION_CREATE = "create"                # chưa có bản ghi → tạo mới (MANUAL)
ACTION_CHANGE_STATUS = "change_status"  # đổi trạng thái đã lưu → cần lý do + AttendanceLog (BR6)
ACTION_UPDATE_NOTE = "update_note"      # chỉ đổi ghi chú → không ghi lịch sử
ACTION_UNCHANGED = "unchanged"          # giữ nguyên


# ======================================================================================
# Phần 1 – Quy tắc thuần
# ======================================================================================
@dataclass(frozen=True)
class AttendanceEntry:
    """Một dòng điểm danh đã kiểm tra hợp lệ về hình thức."""

    student_id: int
    status: AttendanceStatus
    note: Any            # str | None | KEEP_NOTE
    reason: str | None   # đã strip; None nếu không nhập


@dataclass(frozen=True)
class PlannedChange:
    action: str
    entry: AttendanceEntry
    old_status: AttendanceStatus | None = None


def clean_note(value: Any) -> str | None:
    """Ghi chú: bỏ khoảng trắng đầu/cuối, rỗng → None, tối đa 255 ký tự."""
    note = optional_text(value)
    if note is not None and len(note) > MAX_NOTE_LENGTH:
        raise invalid(f"Ghi chú tối đa {MAX_NOTE_LENGTH} ký tự.")
    return note


def normalize_records(records: Any) -> list[AttendanceEntry]:
    """records: [{student_id, status, note?, reason?}] → list[AttendanceEntry].

    Lỗi hình thức → VALIDATION_ERROR. Mỗi sinh viên chỉ xuất hiện một lần (BR1).
    """
    if not isinstance(records, (list, tuple)) or not records:
        raise invalid("Chưa có dữ liệu điểm danh để lưu.")

    entries: list[AttendanceEntry] = []
    seen: set[int] = set()
    for rec in records:
        if not isinstance(rec, Mapping) or "student_id" not in rec or "status" not in rec:
            raise invalid("Mỗi dòng điểm danh phải có student_id và status.")
        student_id = to_positive_int(rec["student_id"], "student_id")
        if student_id in seen:
            raise invalid("Mỗi sinh viên chỉ được điểm danh một lần trong một buổi.")
        seen.add(student_id)

        reason = optional_text(rec.get("reason"))
        if reason is not None and len(reason) > MAX_REASON_LENGTH:
            raise invalid(f"Lý do tối đa {MAX_REASON_LENGTH} ký tự.")
        entries.append(AttendanceEntry(
            student_id=student_id,
            status=parse_status(rec["status"]),
            note=clean_note(rec["note"]) if "note" in rec else KEEP_NOTE,
            reason=reason,
        ))
    return entries


def plan_changes(existing: Mapping[int, tuple[AttendanceStatus, str | None]],
                 entries: list[AttendanceEntry]) -> list[PlannedChange]:
    """Quyết định việc cần làm với từng dòng.

    existing: {student_id: (trạng thái đã lưu, ghi chú đã lưu)} của buổi học này.
    Đổi trạng thái của bản ghi đã lưu mà thiếu lý do → REASON_REQUIRED, báo một lần cho cả danh sách
    để giảng viên bổ sung hết rồi lưu lại (không lưu gì cả).
    """
    plan: list[PlannedChange] = []
    missing_reason: list[int] = []
    for entry in entries:
        current = existing.get(entry.student_id)
        if current is None:
            plan.append(PlannedChange(ACTION_CREATE, entry))
            continue
        old_status, old_note = current
        if entry.status != old_status:
            if not entry.reason:
                missing_reason.append(entry.student_id)
            plan.append(PlannedChange(ACTION_CHANGE_STATUS, entry, old_status))
        elif entry.note is not KEEP_NOTE and entry.note != old_note:
            plan.append(PlannedChange(ACTION_UPDATE_NOTE, entry, old_status))
        else:
            plan.append(PlannedChange(ACTION_UNCHANGED, entry, old_status))

    if missing_reason:
        if len(missing_reason) == 1:
            message = "Sửa điểm danh phải nhập lý do."
        else:
            message = f"Phải nhập lý do cho {len(missing_reason)} sinh viên bị đổi trạng thái đã lưu."
        raise ServiceError(REASON_REQUIRED, message, 400)
    return plan


_FORM_KEY = re.compile(r"^(status|note|reason)\[(\d+)\]$")


def parse_attendance_form(form: Mapping[str, str]) -> list[dict]:
    """Đọc form M09 (`status[<id>]`, `note[<id>]`, `reason[<id>]`) thành `records` cho take_attendance.

    Dòng chưa chọn trạng thái và không nhập gì thì bỏ qua (chưa điểm danh người đó).
    Dòng đã nhập ghi chú/lý do mà chưa chọn trạng thái → VALIDATION_ERROR (tránh mất dữ liệu âm thầm).
    """
    rows: dict[int, dict[str, str]] = {}
    for key, value in form.items():
        match = _FORM_KEY.match(key)
        if match:
            rows.setdefault(int(match.group(2)), {})[match.group(1)] = value

    records: list[dict] = []
    for student_id, fields in rows.items():
        if not (fields.get("status") or "").strip():
            if (fields.get("note") or "").strip() or (fields.get("reason") or "").strip():
                raise invalid("Có sinh viên đã nhập ghi chú hoặc lý do nhưng chưa chọn trạng thái.")
            continue
        records.append({
            "student_id": student_id,
            "status": fields["status"],
            "note": fields.get("note", ""),
            "reason": fields.get("reason", ""),
        })
    return records


# ======================================================================================
# Phần 2 – Service
# ======================================================================================
class ManualAttendanceMixin:
    @staticmethod
    def get_attendance_sheet(lecturer_id: int, session_id: int) -> dict:
        """Dữ liệu trang M09: danh sách sinh viên đã đăng ký kèm trạng thái hiện có.

        - Đã có bản ghi (kể cả sinh viên tự điểm danh bằng mã → Có mặt) thì hiện đúng trạng thái đó.
        - Chưa có bản ghi mà có đơn nghỉ đã duyệt thì điền sẵn Có phép (`attendance_id` vẫn là None).
        - Còn lại `status` là None (giảng viên tự chọn).
        Trả về {session, students[], has_saved} đúng như hợp đồng M09.
        """
        class_session = ManualAttendanceMixin._get_owned_session(lecturer_id, session_id)
        section = class_session.section

        # 3 truy vấn cố định, không phụ thuộc số sinh viên (NFR5)
        students = (
            Student.query
            .join(Enrollment, Enrollment.student_id == Student.user_id)
            .filter(Enrollment.section_id == section.id)
            .order_by(Student.student_code)
            .all()
        )
        attendances = {
            a.student_id: a
            for a in Attendance.query.filter(Attendance.session_id == class_session.id).all()
        }
        excused_ids = {
            student_id
            for (student_id,) in db.session.query(LeaveRequest.student_id).filter(
                LeaveRequest.session_id == class_session.id,
                LeaveRequest.status == LeaveStatus.APPROVED,
            )
        }

        rows = []
        for student in students:
            attendance = attendances.get(student.user_id)
            if attendance is not None:
                status, method, note, attendance_id = (
                    attendance.status, attendance.method, attendance.note or "", attendance.id)
            else:
                status = AttendanceStatus.EXCUSED if student.user_id in excused_ids else None
                method, note, attendance_id = None, "", None
            rows.append({
                "student_id": student.user_id,
                "student_code": student.student_code,
                "full_name": student.full_name,
                "attendance_id": attendance_id,
                "status": status,
                "method": method,
                "note": note,
            })

        return {
            "session": {
                "id": class_session.id,
                "section_id": section.id,
                "course_name": section.course.name,
                "session_date": class_session.session_date,
                "start_time": class_session.start_time,
                "end_time": class_session.end_time,
            },
            "students": rows,
            "has_saved": bool(attendances),
        }

    @staticmethod
    def take_attendance(lecturer_id: int, session_id: int, records: list[dict]) -> list[Attendance]:
        """UC5 – lưu điểm danh cả buổi trong một giao dịch.

        records: [{student_id, status, note?, reason?}]. Với mỗi dòng:
        - chưa có bản ghi → tạo mới, phương thức MANUAL (BR1: mỗi sinh viên một bản ghi mỗi buổi);
        - đã có bản ghi, đổi trạng thái → bắt buộc `reason`, gọi `Attendance.update_status` (UC7) để cập nhật
          và thêm AttendanceLog (BR6);
        - đã có bản ghi, chỉ đổi ghi chú → cập nhật, không ghi lịch sử; không đổi gì → giữ nguyên
          (bản ghi do sinh viên tự điểm danh bằng mã vẫn giữ phương thức QR_PIN).

        Lỗi: NOT_FOUND, NOT_OWNER_SECTION (BR4), VALIDATION_ERROR, NOT_ENROLLED (BR3), REASON_REQUIRED,
        DUPLICATE_ATTENDANCE (hai yêu cầu ghi trùng cùng lúc). Sau khi lưu, gọi kiểm tra ngưỡng vắng.
        """
        class_session = ManualAttendanceMixin._get_owned_session(lecturer_id, session_id)
        session_pk, section_id = class_session.id, class_session.section_id

        entries = normalize_records(records)
        student_ids = [entry.student_id for entry in entries]
        ManualAttendanceMixin._ensure_enrolled(section_id, student_ids)

        existing = {
            a.student_id: a
            for a in Attendance.query.filter(
                Attendance.session_id == session_pk, Attendance.student_id.in_(student_ids)).all()
        }
        plan = plan_changes({sid: (a.status, a.note) for sid, a in existing.items()}, entries)

        results: list[Attendance] = []
        touched: list[int] = []  # sinh viên có bản ghi mới hoặc đổi trạng thái → cần kiểm tra ngưỡng vắng
        try:
            for item in plan:
                entry = item.entry
                if item.action == ACTION_CREATE:
                    attendance = Attendance(
                        session_id=session_pk,
                        student_id=entry.student_id,
                        status=entry.status,
                        method=CheckInMethod.MANUAL,
                        note=None if entry.note is KEEP_NOTE else entry.note,
                    )
                    db.session.add(attendance)
                    touched.append(entry.student_id)
                else:
                    attendance = existing[entry.student_id]
                    if item.action == ACTION_CHANGE_STATUS:
                        attendance.update_status(entry.status, lecturer_id, entry.reason)
                        touched.append(entry.student_id)
                    if entry.note is not KEEP_NOTE and entry.note != attendance.note:
                        attendance.note = entry.note
                results.append(attendance)
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise ServiceError(
                DUPLICATE_ATTENDANCE,
                "Điểm danh buổi này vừa được ghi bởi một yêu cầu khác (ví dụ sinh viên vừa tự điểm danh). "
                "Hãy tải lại trang rồi lưu lại.",
                409,
            ) from exc
        except Exception:
            db.session.rollback()
            raise

        run_threshold_checks(section_id, touched)
        return results

    # ---------------------------------------------------------------- hàm phụ
    @staticmethod
    def _get_owned_session(lecturer_id: int, session_id: int) -> ClassSession:
        """Buổi học tồn tại và thuộc lớp do giảng viên này phụ trách (QT4)."""
        class_session = db.session.get(ClassSession, to_positive_int(session_id, "session_id"))
        if class_session is None:
            raise ServiceError(NOT_FOUND, "Không tìm thấy buổi học.", 404)
        if class_session.section.lecturer_id != lecturer_id:
            raise ServiceError(NOT_OWNER_SECTION, "Bạn không phụ trách lớp học phần này.", 403)
        return class_session

    @staticmethod
    def _ensure_enrolled(section_id: int, student_ids: list[int]) -> None:
        """Mọi sinh viên trong danh sách phải thuộc lớp (QT3), nếu không thì không lưu gì."""
        enrolled = set(db.session.scalars(
            db.select(Enrollment.student_id).where(
                Enrollment.section_id == section_id, Enrollment.student_id.in_(student_ids))
        ))
        missing = [sid for sid in student_ids if sid not in enrolled]
        if missing:
            codes = {s.user_id: s.student_code for s in Student.query.filter(Student.user_id.in_(missing))}
            who = ", ".join(codes.get(sid, f"#{sid}") for sid in missing)
            raise ServiceError(NOT_ENROLLED, f"Sinh viên chưa đăng ký lớp này: {who}.", 400)
