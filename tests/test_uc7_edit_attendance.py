from app.errors import NOT_FOUND, NOT_OWNER_SECTION, REASON_REQUIRED, VALIDATION_ERROR
from app.extensions import db
from app.models import Attendance, AttendanceLog, AttendanceStatus as S, CheckInMethod, Lecturer
from app.services.attendance_service import AttendanceService
from attendance_fixtures import (  # noqa: F401 - fixture được pytest nhận qua import
    add_attendance, app, fails_with, saved, world,
)


def test_edit_attendance_updates_status_and_adds_exactly_one_log(world):
    s1 = world.students[0]
    attendance_id = add_attendance(world, s1, S.ABSENT)

    log = AttendanceService.edit_attendance(world.gv1, attendance_id, "LATE", "  Sinh viên đến trễ 20 phút  ")

    assert isinstance(log, AttendanceLog)
    assert (log.old_status, log.new_status, log.reason, log.changed_by) == (
        S.ABSENT, S.LATE, "Sinh viên đến trễ 20 phút", world.gv1)
    assert log.changed_at is not None
    assert saved(world, s1).status is S.LATE
    assert AttendanceLog.query.count() == 1


def test_edit_attendance_requires_reason(world):
    s1 = world.students[0]
    attendance_id = add_attendance(world, s1, S.ABSENT)
    for blank in (None, "", "   "):
        fails_with(REASON_REQUIRED, AttendanceService.edit_attendance, world.gv1, attendance_id, "LATE", blank)
    assert saved(world, s1).status is S.ABSENT       # thiếu lý do thì không lưu
    assert AttendanceLog.query.count() == 0


def test_edit_attendance_only_by_responsible_lecturer(world):
    s1 = world.students[0]
    attendance_id = add_attendance(world, s1, S.ABSENT)
    fails_with(NOT_OWNER_SECTION, AttendanceService.edit_attendance, world.gv2, attendance_id, "LATE", "Có lý do")
    assert saved(world, s1).status is S.ABSENT
    assert AttendanceLog.query.count() == 0


def test_edit_attendance_not_found_and_bad_input(world):
    fails_with(NOT_FOUND, AttendanceService.edit_attendance, world.gv1, 99999, "LATE", "Có lý do")
    attendance_id = add_attendance(world, world.students[0], S.ABSENT)
    fails_with(VALIDATION_ERROR, AttendanceService.edit_attendance, world.gv1, attendance_id, "SICK", "Có lý do")
    fails_with(VALIDATION_ERROR, AttendanceService.edit_attendance, world.gv1, attendance_id, "ABSENT", "Có lý do")
    assert AttendanceLog.query.count() == 0           # không đổi gì thì không có dòng lịch sử


def test_each_successful_edit_adds_one_log_and_history_is_kept(world):
    attendance_id = add_attendance(world, world.students[0], S.PRESENT)
    AttendanceService.edit_attendance(world.gv1, attendance_id, "ABSENT", "Lần 1")
    AttendanceService.edit_attendance(world.gv1, attendance_id, "EXCUSED", "Lần 2: có đơn")
    db.session.expire_all()
    logs = db.session.get(Attendance, attendance_id).logs
    assert [(l.old_status, l.new_status, l.reason) for l in logs] == [
        (S.PRESENT, S.ABSENT, "Lần 1"), (S.ABSENT, S.EXCUSED, "Lần 2: có đơn")]


def test_edit_keeps_original_check_in_method(world):
    """Sửa bản ghi sinh viên tự điểm danh bằng mã: đổi trạng thái + có lịch sử, phương thức vẫn là QR_PIN."""
    s1 = world.students[0]
    attendance_id = add_attendance(world, s1, S.PRESENT, CheckInMethod.QR_PIN)
    AttendanceService.edit_attendance(world.gv1, attendance_id, "LATE", "Vào lớp trễ 15 phút")
    attendance = saved(world, s1)
    assert (attendance.status, attendance.method) == (S.LATE, CheckInMethod.QR_PIN)
    assert AttendanceLog.query.count() == 1


def test_update_status_does_not_commit(world):
    """`Attendance.update_status` chỉ chuẩn bị thay đổi; rollback thì cả trạng thái lẫn lịch sử đều mất (NFR3)."""
    attendance_id = add_attendance(world, world.students[0], S.PRESENT)
    attendance = db.session.get(Attendance, attendance_id)

    log = attendance.update_status("ABSENT", world.gv1, "Thử")
    assert (log.old_status, log.new_status) == (S.PRESENT, S.ABSENT)
    db.session.rollback()

    assert db.session.get(Attendance, attendance_id).status is S.PRESENT
    assert AttendanceLog.query.count() == 0


def test_update_status_checks_owner_by_itself(world):
    """Kiểm tra QT4 nằm ngay ở update_status, không chỉ ở service."""
    attendance = db.session.get(Attendance, add_attendance(world, world.students[0], S.PRESENT))
    fails_with(NOT_OWNER_SECTION, attendance.update_status, "LATE", world.gv2, "Có lý do")


def test_threshold_check_runs_after_edit(world, monkeypatch):
    calls = []
    monkeypatch.setattr(
        AttendanceService, "check_absence_threshold",
        staticmethod(lambda student_id, section_id: calls.append((student_id, section_id))), raising=False)
    s1 = world.students[0]
    attendance_id = add_attendance(world, s1, S.PRESENT)
    AttendanceService.edit_attendance(world.gv1, attendance_id, "ABSENT", "Nhập nhầm")
    assert calls == [(s1, world.section)]


def test_lecturer_edit_attendance_follows_class_diagram(world):
    """Lecturer.edit_attendance gọi đúng service."""
    attendance_id = add_attendance(world, world.students[0], S.PRESENT)
    lecturer = db.session.get(Lecturer, world.gv1)
    log = lecturer.edit_attendance(attendance_id, "LATE", "Đến trễ")
    assert (log.old_status, log.new_status, log.changed_by) == (S.PRESENT, S.LATE, world.gv1)
