"""Dữ liệu mẫu thuần Python (không phụ thuộc Flask/SQLAlchemy) để seed.py dùng và để kiểm tra riêng."""
from datetime import date, time, timedelta

SEMESTER = "2026-1"
START_DATE = date(2026, 10, 5)  # thứ Hai
SESSIONS_PER_SECTION = 10
HELD_SESSIONS = 6               # 6 buổi đầu đã diễn ra và có dữ liệu điểm danh
OPEN_CODE_SESSION = 7           # buổi 7 của lớp S1 đang mở mã điểm danh để thử check-in
OPEN_CODE = "123456"

ADMIN = {"username": "admin", "password": "admin123", "full_name": "Quản trị viên", "email": "admin@school.edu.vn"}

LECTURERS = [
    {"username": "gv01", "password": "gv123", "full_name": "Nguyễn Văn An", "email": "gv01@school.edu.vn",
     "lecturer_code": "GV001", "department": "Công nghệ thông tin"},
    {"username": "gv02", "password": "gv123", "full_name": "Trần Thị Bình", "email": "gv02@school.edu.vn",
     "lecturer_code": "GV002", "department": "Công nghệ thông tin"},
    {"username": "gv03", "password": "gv123", "full_name": "Lê Quang Cường", "email": "gv03@school.edu.vn",
     "lecturer_code": "GV003", "department": "Kỹ thuật phần mềm"},
]

STUDENT_NAMES = [
    "Phạm Minh Anh", "Nguyễn Hoàng Bảo", "Trần Thu Cúc", "Lê Đức Dũng", "Võ Ngọc Hà",
    "Đặng Gia Huy", "Bùi Khánh Linh", "Hoàng Thế Minh", "Ngô Phương Nam", "Đỗ Thảo Nguyên",
    "Dương Quốc Phong", "Lý Mai Quỳnh", "Phan Thanh Sơn", "Vũ Thùy Trang", "Trịnh Anh Tuấn",
    "Huỳnh Bích Uyên", "Mai Văn Vinh", "Đinh Hải Yến", "Tạ Quốc Khánh", "Châu Lan Phương",
]
STUDENTS = [
    {"username": f"sv{i:02d}", "password": "sv123", "full_name": name, "email": f"sv{i:02d}@school.edu.vn",
     "student_code": f"SV2024{i:03d}", "class_name": "CNTT-K24A" if i <= 10 else "CNTT-K24B"}
    for i, name in enumerate(STUDENT_NAMES, start=1)
]

COURSES = [
    {"code": "INT1001", "name": "Lập trình Python", "credits": 3},
    {"code": "INT1002", "name": "Cơ sở dữ liệu", "credits": 3},
    {"code": "INT1003", "name": "Công nghệ phần mềm", "credits": 3},
]

# students: số thứ tự sinh viên (1..20) đăng ký lớp; day_offset: lệch thứ trong tuần so với START_DATE
SECTIONS = [
    {"key": "S1", "course": "INT1001", "lecturer": "gv01", "room": "A101", "students": range(1, 13),
     "day_offset": 0, "start": time(7, 0), "end": time(9, 30)},
    {"key": "S2", "course": "INT1001", "lecturer": "gv02", "room": "A102", "students": range(9, 21),
     "day_offset": 1, "start": time(9, 30), "end": time(12, 0)},
    {"key": "S3", "course": "INT1002", "lecturer": "gv02", "room": "B201", "students": range(1, 15),
     "day_offset": 2, "start": time(13, 0), "end": time(15, 30)},
    {"key": "S4", "course": "INT1003", "lecturer": "gv03", "room": "B202", "students": range(5, 19),
     "day_offset": 3, "start": time(15, 30), "end": time(18, 0)},
]

# (lớp, số thứ tự sinh viên, số buổi) -> trạng thái; bảo đảm đủ 4 trạng thái và 1 sinh viên vắng > 20%
OVERRIDES = {
    ("S1", 5, 1): "ABSENT", ("S1", 5, 2): "ABSENT", ("S1", 5, 3): "ABSENT",  # sv05: 3/6 = 50% > 20%
    ("S1", 1, 1): "LATE",
    ("S1", 2, 2): "EXCUSED",   # khớp đơn nghỉ đã duyệt của sv02
    ("S1", 1, 5): "LATE",      # từng bị ghi ABSENT, giảng viên sửa thành LATE (có AttendanceLog)
}
PENDING_LEAVE = {"student": 4, "section": "S1", "session_no": 8, "reason": "Đi khám bệnh theo lịch hẹn."}
APPROVED_LEAVE = {"student": 2, "section": "S1", "session_no": 2, "reason": "Có việc gia đình đột xuất.",
                  "reviewer": "gv01"}
EDIT_LOG = {"section": "S1", "student": 1, "session_no": 5, "old": "ABSENT", "new": "LATE", "editor": "gv01",
            "reason": "Sinh viên đến trễ 20 phút, nhập nhầm là vắng."}


def session_date(section, session_no):
    return START_DATE + timedelta(days=section["day_offset"] + 7 * (session_no - 1))


def planned_status(section_key, student_no, session_no):
    """Trạng thái điểm danh dự kiến (chuỗi tên enum AttendanceStatus), xác định, không ngẫu nhiên."""
    if (section_key, student_no, session_no) in OVERRIDES:
        return OVERRIDES[(section_key, student_no, session_no)]
    if section_key == "S1" and student_no == 5:
        return "PRESENT"
    if (student_no + 3 * session_no) % 17 == 0:
        return "ABSENT"  # mỗi sinh viên tối đa 1 buổi trong 6 buổi (≈16,7% < 20%)
    if (student_no + session_no) % 9 == 0:
        return "LATE"
    return "PRESENT"


def absence_report():
    """{(lớp, sinh viên): (số ABSENT, số buổi đã diễn ra)} – dùng để kiểm tra dữ liệu mẫu."""
    out = {}
    for sec in SECTIONS:
        for k in sec["students"]:
            absent = sum(planned_status(sec["key"], k, n) == "ABSENT" for n in range(1, HELD_SESSIONS + 1))
            out[(sec["key"], k)] = (absent, HELD_SESSIONS)
    return out
