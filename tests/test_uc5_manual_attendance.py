import time

import pytest
from sqlalchemy.exc import IntegrityError

from app.errors import (
    DUPLICATE_ATTENDANCE, NOT_ENROLLED, NOT_FOUND, NOT_OWNER_SECTION, REASON_REQUIRED, VALIDATION_ERROR,
)
from app.extensions import db
from app.models import (
    Attendance, AttendanceLog, AttendanceStatus as S, CheckInMethod, Enrollment, LeaveRequest, LeaveStatus,
    Lecturer, Student,
)
from app.services.attendance_service import AttendanceService
from attendance_fixtures import (  # noqa: F401 - fixture được pytest nhận qua import
    add_attendance, app, client, fails_with, login, make_student, saved, url, world,
)


# ============================================================================= lưu điểm danh
def test_take_attendance_creates_manual_records(world):
    s1, s2, s3 = world.students
    result = AttendanceService.take_attendance(world.gv1, world.session, [
        {"student_id": s1, "status": "PRESENT"},
        {"student_id": s2, "status": "ABSENT", "note": "Báo ốm"},
        {"student_id": s3, "status": S.LATE},
    ])
    assert len(result) == 3
    assert Attendance.query.count() == 3
    a2 = saved(world, s2)
    assert (a2.status, a2.method, a2.note, a2.check_in_time) == (S.ABSENT, CheckInMethod.MANUAL, "Báo ốm", None)
    assert saved(world, s3).status is S.LATE
    assert AttendanceLog.query.count() == 0  # tạo mới thì không có lịch sử sửa


def test_take_attendance_only_for_own_section(world):
    fails_with(NOT_OWNER_SECTION, AttendanceService.take_attendance, world.gv2, world.session,
               [{"student_id": world.students[0], "status": "PRESENT"}])
    assert Attendance.query.count() == 0


def test_take_attendance_unknown_session(world):
    fails_with(NOT_FOUND, AttendanceService.take_attendance, world.gv1, 99999,
               [{"student_id": world.students[0], "status": "PRESENT"}])


def test_take_attendance_rejects_student_not_in_class_and_saves_nothing(world):
    error = fails_with(NOT_ENROLLED, AttendanceService.take_attendance, world.gv1, world.session, [
        {"student_id": world.students[0], "status": "PRESENT"},   # hợp lệ nhưng không được lưu
        {"student_id": world.outsider, "status": "PRESENT"},      # SV004 không thuộc lớp (QT3)
    ])
    assert "SV004" in error.message
    assert Attendance.query.count() == 0


def test_take_attendance_invalid_status_saves_nothing(world):
    s1, s2, _ = world.students
    fails_with(VALIDATION_ERROR, AttendanceService.take_attendance, world.gv1, world.session,
               [{"student_id": s1, "status": "PRESENT"}, {"student_id": s2, "status": "SICK"}])
    assert Attendance.query.count() == 0


def test_take_attendance_rejects_duplicate_student_and_empty_payload(world):
    s1 = world.students[0]
    fails_with(VALIDATION_ERROR, AttendanceService.take_attendance, world.gv1, world.session,
               [{"student_id": s1, "status": "PRESENT"}, {"student_id": s1, "status": "ABSENT"}])
    fails_with(VALIDATION_ERROR, AttendanceService.take_attendance, world.gv1, world.session, [])
    assert Attendance.query.count() == 0


def test_resubmitting_same_data_changes_nothing(world):
    s1, s2, _ = world.students
    records = [{"student_id": s1, "status": "PRESENT"}, {"student_id": s2, "status": "ABSENT", "note": "ốm"}]
    AttendanceService.take_attendance(world.gv1, world.session, records)
    AttendanceService.take_attendance(world.gv1, world.session, records)
    assert Attendance.query.count() == 2          # BR1: vẫn một bản ghi mỗi sinh viên
    assert AttendanceLog.query.count() == 0


def test_changing_saved_status_without_reason_saves_nothing(world):
    s1, s2, s3 = world.students
    AttendanceService.take_attendance(world.gv1, world.session, [{"student_id": s1, "status": "PRESENT"}])

    fails_with(REASON_REQUIRED, AttendanceService.take_attendance, world.gv1, world.session, [
        {"student_id": s2, "status": "ABSENT"},                       # mới → lẽ ra được tạo
        {"student_id": s1, "status": "ABSENT"},                       # đổi bản ghi đã lưu, thiếu lý do
        {"student_id": s3, "status": "LATE", "note": "x"},
    ])
    assert Attendance.query.count() == 1                              # không có bản ghi mới nào
    assert saved(world, s1).status is S.PRESENT
    assert AttendanceLog.query.count() == 0


def test_changing_saved_status_with_reason_writes_one_log(world):
    s1, _, _ = world.students
    AttendanceService.take_attendance(world.gv1, world.session, [{"student_id": s1, "status": "PRESENT"}])

    AttendanceService.take_attendance(world.gv1, world.session, [
        {"student_id": s1, "status": "LATE", "reason": "Đến trễ 20 phút"}])

    assert saved(world, s1).status is S.LATE
    logs = AttendanceLog.query.all()
    assert len(logs) == 1
    assert (logs[0].old_status, logs[0].new_status, logs[0].reason, logs[0].changed_by) == (
        S.PRESENT, S.LATE, "Đến trễ 20 phút", world.gv1)


def test_student_self_check_in_is_kept_when_unchanged(world):
    s1, s2, _ = world.students
    add_attendance(world, s1, S.PRESENT, CheckInMethod.QR_PIN)       # sinh viên đã tự điểm danh bằng mã
    AttendanceService.take_attendance(world.gv1, world.session, [
        {"student_id": s1, "status": "PRESENT"}, {"student_id": s2, "status": "ABSENT"}])
    a1 = saved(world, s1)
    assert (a1.status, a1.method) == (S.PRESENT, CheckInMethod.QR_PIN)   # không bị ghi đè thành MANUAL
    assert AttendanceLog.query.count() == 0


def test_note_only_change_needs_no_reason_and_no_log(world):
    s1 = world.students[0]
    AttendanceService.take_attendance(world.gv1, world.session, [{"student_id": s1, "status": "LATE", "note": "a"}])
    AttendanceService.take_attendance(world.gv1, world.session, [{"student_id": s1, "status": "LATE", "note": "b"}])
    assert saved(world, s1).note == "b"
    # không truyền note → giữ nguyên; note rỗng → xóa
    AttendanceService.take_attendance(world.gv1, world.session, [{"student_id": s1, "status": "LATE"}])
    assert saved(world, s1).note == "b"
    AttendanceService.take_attendance(world.gv1, world.session, [{"student_id": s1, "status": "LATE", "note": ""}])
    assert saved(world, s1).note is None
    assert AttendanceLog.query.count() == 0


def test_failure_midway_rolls_back_everything(world, monkeypatch):
    """NFR3: lỗi giữa chừng thì không lưu gì (kể cả bản ghi tạo mới trước đó)."""
    s1, s2, s3 = world.students
    AttendanceService.take_attendance(world.gv1, world.session, [{"student_id": s1, "status": "PRESENT"}])

    def boom(self, *args, **kwargs):
        raise RuntimeError("lỗi giữa chừng")

    monkeypatch.setattr(Attendance, "update_status", boom)
    with pytest.raises(RuntimeError):
        AttendanceService.take_attendance(world.gv1, world.session, [
            {"student_id": s2, "status": "ABSENT"},                                  # tạo mới (làm trước)
            {"student_id": s1, "status": "LATE", "reason": "đến muộn"},              # nổ ở đây
            {"student_id": s3, "status": "PRESENT"},
        ])
    monkeypatch.undo()
    assert Attendance.query.count() == 1
    assert saved(world, s1).status is S.PRESENT


def test_concurrent_duplicate_maps_to_duplicate_attendance(world, monkeypatch):
    def fake_commit():
        raise IntegrityError("INSERT INTO attendances", {}, Exception("UNIQUE constraint failed"))

    monkeypatch.setattr(db.session, "commit", fake_commit)
    error = fails_with(DUPLICATE_ATTENDANCE, AttendanceService.take_attendance, world.gv1, world.session,
                       [{"student_id": world.students[0], "status": "PRESENT"}])
    assert error.http_status == 409
    monkeypatch.undo()
    assert Attendance.query.count() == 0


def test_save_100_students_within_two_seconds(world):
    """NFR5: lưu lớp 100 sinh viên (và sửa cả 100 kèm lý do) không quá 2 giây."""
    extra = [make_student(100 + i) for i in range(100)]
    db.session.add_all(extra)
    db.session.flush()
    db.session.add_all(Enrollment(section_id=world.section, student_id=s.id) for s in extra)
    db.session.commit()
    ids = [s.id for s in extra]

    started = time.perf_counter()
    AttendanceService.take_attendance(world.gv1, world.session, [{"student_id": i, "status": "PRESENT"} for i in ids])
    first_save = time.perf_counter() - started
    assert Attendance.query.count() == 100
    assert first_save < 2.0

    started = time.perf_counter()
    AttendanceService.take_attendance(world.gv1, world.session, [
        {"student_id": i, "status": "ABSENT", "reason": "Sửa hàng loạt"} for i in ids])
    edit_all = time.perf_counter() - started
    assert AttendanceLog.query.count() == 100
    assert edit_all < 2.0


# ----------------------------------------------------------------------------- gọi kiểm tra ngưỡng vắng (TV2-3)
@pytest.fixture
def threshold_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(
        AttendanceService, "check_absence_threshold",
        staticmethod(lambda student_id, section_id: calls.append((student_id, section_id))), raising=False)
    return calls


def test_threshold_check_runs_for_created_and_changed_students_only(world, threshold_calls):
    s1, s2, s3 = world.students
    AttendanceService.take_attendance(world.gv1, world.session, [
        {"student_id": s1, "status": "PRESENT"}, {"student_id": s2, "status": "ABSENT"}])
    assert threshold_calls == [(s1, world.section), (s2, world.section)]

    threshold_calls.clear()
    AttendanceService.take_attendance(world.gv1, world.session, [
        {"student_id": s1, "status": "ABSENT", "reason": "Nhập nhầm"},   # đổi trạng thái
        {"student_id": s2, "status": "ABSENT"},                          # không đổi
        {"student_id": s3, "status": "PRESENT"},                         # mới
    ])
    assert threshold_calls == [(s1, world.section), (s3, world.section)]


def test_threshold_check_failure_does_not_undo_saved_attendance(world, monkeypatch):
    def boom(student_id, section_id):
        raise RuntimeError("lỗi ở UC15")

    monkeypatch.setattr(AttendanceService, "check_absence_threshold", staticmethod(boom), raising=False)
    AttendanceService.take_attendance(world.gv1, world.session, [{"student_id": world.students[0], "status": "ABSENT"}])
    assert Attendance.query.count() == 1


# ============================================================================= dữ liệu cho M09
def test_sheet_prefills_checked_in_and_excused(world):
    s1, s2, s3 = world.students
    add_attendance(world, s1, S.PRESENT, CheckInMethod.QR_PIN)                       # đã tự điểm danh
    db.session.add_all([
        LeaveRequest(student_id=s2, session_id=world.session, reason="Việc gia đình", status=LeaveStatus.APPROVED),
        LeaveRequest(student_id=s3, session_id=world.session, reason="Đi khám", status=LeaveStatus.PENDING),
    ])
    db.session.commit()

    sheet = AttendanceService.get_attendance_sheet(world.gv1, world.session)

    rows = {r["student_code"]: r for r in sheet["students"]}
    assert list(rows) == ["SV001", "SV002", "SV003"]                                  # chỉ SV đã đăng ký, theo mã
    assert (rows["SV001"]["status"], rows["SV001"]["method"]) == (S.PRESENT, CheckInMethod.QR_PIN)
    assert rows["SV001"]["attendance_id"] is not None
    assert (rows["SV002"]["status"], rows["SV002"]["attendance_id"]) == (S.EXCUSED, None)   # điền sẵn Có phép
    assert rows["SV003"]["status"] is None                                            # đơn chờ duyệt: chưa điền
    assert sheet["has_saved"] is True
    assert sheet["session"]["id"] == world.session and sheet["session"]["course_name"] == "Lập trình Python"


def test_sheet_without_data_and_ownership(world):
    sheet = AttendanceService.get_attendance_sheet(world.gv1, world.session)
    assert sheet["has_saved"] is False and all(r["status"] is None for r in sheet["students"])
    fails_with(NOT_OWNER_SECTION, AttendanceService.get_attendance_sheet, world.gv2, world.session)
    fails_with(NOT_FOUND, AttendanceService.get_attendance_sheet, world.gv1, 99999)


def test_lecturer_methods_follow_class_diagram(world):
    """Lecturer.take_attendance / get_attendance_sheet gọi đúng service."""
    s1 = world.students[0]
    lecturer = db.session.get(Lecturer, world.gv1)
    lecturer.take_attendance(world.session, [{"student_id": s1, "status": "PRESENT"}])
    assert saved(world, s1).status is S.PRESENT
    assert lecturer.get_attendance_sheet(world.session)["has_saved"] is True


# ============================================================================= controller M09
def test_m09_requires_login_and_lecturer_role(world, client):
    r = client.get(url(world))
    assert r.status_code == 302 and "/login" in r.headers["Location"]

    db.session.add(Student(username="svlogin", password="sv123", full_name="SV", email="svl@x.vn", student_code="SV900"))
    db.session.commit()
    login(client, "svlogin", "sv123")
    assert client.get(url(world)).status_code == 403
    assert client.post(url(world), data={"status[1]": "PRESENT"}).status_code == 403


def test_m09_other_lecturer_gets_403_and_nothing_saved(world, client):
    login(client, "gv02")
    assert client.get(url(world)).status_code == 403
    r = client.post(url(world), data={f"status[{world.students[0]}]": "PRESENT"})
    assert r.status_code == 403
    assert Attendance.query.count() == 0


def test_m09_get_passes_contract_variables(world, client):
    login(client, "gv01")
    r = client.get(url(world))
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert f"Lập trình Python|{world.session}|has_saved=False" in body
    assert "SV001=-//;SV002=-//;SV003=-//;" in body
    assert client.get("/lecturer/sessions/99999/attendance").status_code == 404


def test_m09_post_saves_marked_rows_and_redirects(world, client):
    s1, s2, s3 = world.students
    login(client, "gv01")
    r = client.post(url(world), data={
        f"status[{s1}]": "PRESENT", f"note[{s1}]": "", f"reason[{s1}]": "",
        f"status[{s2}]": "ABSENT", f"note[{s2}]": "Báo ốm", f"reason[{s2}]": "",
        f"note[{s3}]": "", f"reason[{s3}]": "",                                       # SV3 chưa chọn → bỏ qua
    })
    assert r.status_code == 302 and r.headers["Location"].endswith(url(world))
    assert saved(world, s1).status is S.PRESENT
    assert (saved(world, s2).status, saved(world, s2).note) == (S.ABSENT, "Báo ốm")
    assert saved(world, s3) is None


def test_m09_post_edit_without_reason_shows_error_keeps_input_and_saves_nothing(world, client):
    s1 = world.students[0]
    add_attendance(world, s1, S.PRESENT)
    login(client, "gv01")
    r = client.post(url(world), data={f"status[{s1}]": "ABSENT", f"note[{s1}]": "", f"reason[{s1}]": ""})
    body = r.get_data(as_text=True)
    assert r.status_code == 400 and f"err={REASON_REQUIRED}" in body
    assert "SV001=ABSENT//;" in body                              # giữ lại lựa chọn vừa nhập
    assert saved(world, s1).status is S.PRESENT
    assert AttendanceLog.query.count() == 0


def test_m09_post_edit_with_reason_writes_log(world, client):
    s1 = world.students[0]
    add_attendance(world, s1, S.PRESENT)
    login(client, "gv01")
    r = client.post(url(world), data={f"status[{s1}]": "ABSENT", f"note[{s1}]": "", f"reason[{s1}]": "Nhập nhầm"})
    assert r.status_code == 302
    assert saved(world, s1).status is S.ABSENT
    assert [(l.reason, l.changed_by) for l in AttendanceLog.query.all()] == [("Nhập nhầm", world.gv1)]


def test_m09_post_with_nothing_selected_is_rejected(world, client):
    login(client, "gv01")
    r = client.post(url(world), data={f"note[{world.students[0]}]": ""})
    assert r.status_code == 400 and f"err={VALIDATION_ERROR}" in r.get_data(as_text=True)
    assert Attendance.query.count() == 0
