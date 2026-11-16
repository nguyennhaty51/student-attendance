# Hệ thống điểm danh sinh viên – Nhóm 10

Ứng dụng web Flask (kiến trúc MVC, Mục 7.1 của tài liệu). Phần TV1 (ngày 1–2): lớp đối tượng, CSDL, dữ liệu mẫu, hợp đồng frontend–backend.

## Cấu trúc

```
app/
  __init__.py        create_app, bật khóa ngoại cho SQLite, trang 403
  extensions.py      db, migrate, login_manager, csrf
  errors.py          ServiceError + mã lỗi dùng chung
  models/            lớp đối tượng + ánh xạ bảng (enums, user, academic, attendance, misc)
  routes/            controller (auth.py: đăng nhập, đăng xuất, đổi mật khẩu)
  services/          nghiệp vụ (auth_service.py)
  utils/decorators.py   role_required(...)
  templates/         base.html, macros.html, auth/, errors/
config.py            cấu hình ở thư mục gốc (DATABASE_URL, ngưỡng vắng 20%, PIN 6 số / 5 phút)
scripts/
  seed.py            nạp dữ liệu mẫu (chạy lại được nhiều lần)
  seed_data.py       dữ liệu mẫu thuần Python
  check_constraints.py   thử chèn trùng/khóa ngoại sai: phải bị CSDL từ chối
docs/api_contract.md hợp đồng frontend–backend (M01–M15, chữ ký service, mã lỗi)
wsgi.py              điểm vào cho `flask --app wsgi`
```
## Cài đặt và chạy

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# SQLite (mặc định, file instance/attendance.sqlite3)
flask --app wsgi db upgrade
python scripts/seed.py
python scripts/check_constraints.py        # mọi dòng phải là "OK    bị từ chối"

# MySQL
export DATABASE_URL="mysql+pymysql://user:pass@localhost/attendance?charset=utf8mb4"
flask --app wsgi db upgrade && python scripts/seed.py
```

**Lần đầu tạo migration** (chỉ TV1 làm, rồi commit thư mục `migrations/`):

```bash
flask --app wsgi db init
flask --app wsgi db migrate -m "initial schema"
flask --app wsgi db upgrade
```

Kiểm tra file migration sinh ra trên cả SQLite và MySQL trước khi commit (cột ENUM, TINYINT, CHAR(6)).

## Cơ sở dữ liệu (Hình 6.1) – 11 bảng

`users`, `students`, `lecturers`, `courses`, `class_sections`, `enrollments`, `class_sessions`, `attendances`, `attendance_logs`, `leave_requests`, `notifications`.
`Report` chỉ có trong sơ đồ lớp, không có bảng. `Admin` dùng chung bảng `users` (cột `role`).

| Ràng buộc | Nơi khai báo |
|---|---|
| UNIQUE `(session_id, student_id)` – BR1, NFR4 | `attendances` (`uq_attendances_session_student`) |
| UNIQUE `(section_id, student_id)` | `enrollments` |
| UNIQUE `(student_id, session_id)` | `leave_requests` (theo ERD) |
| UNIQUE `username`, `email` | `users` |
| UNIQUE `student_code` / `lecturer_code` / `code` (mã môn) | `students` / `lecturers` / `courses` |
| ENUM `role`, `status`, `method`, đơn nghỉ `status` | `users.role`, `attendances.status/method`, `attendance_logs.old_status/new_status`, `leave_requests.status` |

Enum lưu tên viết hoa (`PRESENT`, `QR_PIN`...): MySQL dùng ENUM thật, SQLite dùng VARCHAR + CHECK.

## Ánh xạ sơ đồ lớp (Hình 5.1) ↔ Python ↔ use case

Tên lớp và thuộc tính giữ như sơ đồ, viết `snake_case` (ví dụ `passwordHash` → `password_hash`). Thân phương thức tạm là `raise NotImplementedError("TODO TVx: ...")` để TV2/TV3 điền (hoặc gọi service); riêng `generate_code`, `is_code_valid`, `mark_as_read`, `login`, `set_password`, `check_password` đã viết sẵn vì chỉ dùng dữ liệu của chính đối tượng.

| Phương thức trong sơ đồ | Hàm Python | Use case | Người điền |
|---|---|---|---|
| `User.login()` | `User.login(password)` | UC1 | TV2 |
| `User.logout()` | `User.logout()` | UC1 | TV2 |
| `User.changePassword()` | `User.change_password(old_password, new_password)` | UC14 | TV2 |
| `Student.viewAttendanceHistory()` | `Student.view_attendance_history(section_id=None)` | UC2 | TV2 |
| `Student.checkIn(code)` | `Student.check_in(code)` | UC3 | TV2 |
| `Student.submitLeaveRequest()` | `Student.submit_leave_request(session_id, reason)` | UC4 | TV3 |
| `Student.viewNotifications()` | `Student.view_notifications(unread_only=False)` | UC15 | TV3 |
| `Lecturer.viewTeachingClasses()` | `Lecturer.view_teaching_classes()` | UC16 | TV3 |
| `Lecturer.takeAttendance()` | `Lecturer.take_attendance(session_id, records)` | UC5 | TV2 |
| `Lecturer.openCheckInSession()` | `Lecturer.open_check_in_session(session_id, minutes=5)` | UC6 | TV2 |
| `Lecturer.editAttendance()` | `Lecturer.edit_attendance(attendance_id, new_status, reason)` | UC7 | TV2 |
| `Lecturer.reviewLeave()` | `Lecturer.review_leave(leave_id, approve)` | UC8 | TV3 |
| `Lecturer.viewReport()` | `Lecturer.view_report(**filters)` | UC9 | TV3 |
| `Admin.manageUsers()` | `Admin.manage_users(action, **data)` | UC11 | TV3 |
| `Admin.manageSections()` | `Admin.manage_sections(action, **data)` | UC12 | TV3 |
| `Admin.manageSessions()` | `Admin.manage_sessions(action, **data)` | UC13 | TV3 |
| `Admin.viewReport()` | `Admin.view_report(**filters)` | UC9 | TV3 |
| `ClassSection.addStudent()` | `ClassSection.add_student(student_id)` | UC12 | TV3 |
| `ClassSection.getAttendanceRate()` | `ClassSection.get_attendance_rate(student_id=None)` | UC2, UC9, UC15 | TV2 |
| `ClassSession.generateCode()` | `ClassSession.generate_code(minutes=5)` (đã viết) | UC6 | – |
| `ClassSession.isCodeValid()` | `ClassSession.is_code_valid(code=None)` (đã viết) | UC3 | – |
| `Attendance.updateStatus()` | `Attendance.update_status(new_status, changed_by, reason)` | UC7 | TV2 |
| `LeaveRequest.approve()` | `LeaveRequest.approve(lecturer_id)` | UC8 | TV3 |
| `LeaveRequest.reject()` | `LeaveRequest.reject(lecturer_id)` | UC8 | TV3 |
| `Notification.markAsRead()` | `Notification.mark_as_read()` (đã viết) | UC15 | – |
| `Report.generateBySection()` | `Report.generate_by_section(section_id, date_from, date_to)` | UC9 | TV3 |
| `Report.generateByStudent()` | `Report.generate_by_student(student_id, section_id)` | UC9 | TV3 |
| `Report.exportExcel()` | `Report.export_excel(report, path)` | UC10 | TV3 |
| `Report.exportPdf()` | `Report.export_pdf(report, path)` | UC10 | TV3 |

Hàm phụ ngoài sơ đồ (không đổi tên lớp/phương thức của sơ đồ): `User.set_password`, `User.check_password` (băm bcrypt – NFR7), `ClassSession.close_code` (đóng phiên mã sớm, M10).

Kế thừa: `Student`, `Lecturer`, `Admin` kế thừa `User` (lớp trừu tượng: tạo `User(...)` trực tiếp báo `TypeError`).
Kiểm tra ngưỡng vắng (UC15) không phải phương thức trong sơ đồ: nằm ở `AttendanceService.check_absence_threshold` (xem `docs/api_contract.md`).

## Tài khoản mẫu (chỉ dùng khi phát triển)

| Vai trò | Tên đăng nhập | Mật khẩu | Ghi chú |
|---|---|---|---|
| Quản trị viên | `admin` | `admin123` | |
| Giảng viên | `gv01`, `gv02`, `gv03` | `gv123` | gv01: lớp S1; gv02: S2, S3; gv03: S4 |
| Sinh viên | `sv01` … `sv20` | `sv123` | mã SV `SV2024001`…`SV2024020` |

Dữ liệu mẫu: 3 môn (INT1001, INT1002, INT1003), 4 lớp học phần học kỳ `2026-1` (S1, S2: INT1001; S3: INT1002; S4: INT1003), mỗi lớp 10 buổi, 6 buổi đầu đã có điểm danh đủ 4 trạng thái.
- `sv05` vắng 3/6 buổi ở lớp S1 (50% > 20%) và có 1 thông báo cảnh báo.
- 2 đơn nghỉ: `sv02` đã duyệt (buổi 2 của S1 → EXCUSED), `sv04` đang chờ duyệt (buổi 8 của S1).
- 1 bản ghi sửa điểm danh (`attendance_logs`): `sv01`, buổi 5 của S1, ABSENT → LATE.
- Buổi 7 của S1 đang mở mã điểm danh `123456` (gia hạn 1 ngày mỗi lần chạy seed) để thử check-in.

## Quy tắc làm việc

- Làm trên nhánh tách từ `develop`, mở Pull Request vào `develop`; mỗi nhóm việc nhỏ một PR (`feature/t1-models`, `feature/t1-migrations`, `feature/t1-seed`, `docs/api-contract`). PR cuối của Issue ghi `Closes #<số Issue>`.
- Chỉ sửa file thuộc phần của mình; cần đổi file dùng chung (`app/models/*`, `app/errors.py`, `docs/api_contract.md`) thì báo TV1 / mở PR cho TV1.
- Kiểm thử làm sau khi hoàn thành chức năng, theo Testing Document Template của thầy.
## Dùng layout chung (TV4, TV5)

Mọi trang con kế thừa `app/templates/base.html` (thanh trên: tên hệ thống, tên người dùng, đổi mật khẩu, đăng xuất; menu trái theo vai trò đúng Mục 7.2; vùng thông báo; Bootstrap 5 co giãn theo màn hình). **Không sửa `base.html`**; cần đổi thì báo TV1.

```jinja
{% extends "base.html" %}
{% from "macros.html" import status_badge, render_pagination, confirm_modal %}

{% block title %}Lịch sử điểm danh{% endblock %}
{% block extra_css %}{% endblock %}          {# tùy chọn #}
{% block content %}
  <h4>Lịch sử điểm danh</h4>
  ... nội dung trang ...
{% endblock %}
{% block extra_js %}{% endblock %}           {# tùy chọn #}
```

| Block | Dùng cho |
|---|---|
| `title` | Tiêu đề thẻ trình duyệt |
| `content` | Nội dung chính (bên phải menu) |
| `extra_css`, `extra_js` | CSS/JS riêng của trang (JS nạp sau Bootstrap) |

**Thông báo:** trong route gọi `flash("Nội dung", "success")`; loại: `success` (xanh lá), `danger` (đỏ), `warning` (vàng), `info` (xanh dương). `base.html` tự hiển thị.

**Macro** (`app/templates/macros.html`):

| Macro | Cách dùng |
|---|---|
| `status_badge(status)` | `{{ status_badge(row.status) }}`; nhận enum hoặc chuỗi (`PRESENT`/`present`...). Có mặt xanh lá, Vắng đỏ, Muộn vàng, Có phép xanh dương; Chờ duyệt vàng, Đã duyệt xanh lá, Từ chối đỏ |
| `render_pagination(pagination, endpoint, **bộ_lọc)` | `{{ render_pagination(p, 'admin.users', q=q) }}`; `p` là kết quả `query.paginate(page=..., per_page=20)` |
| `confirm_modal(id, tiêu_đề, nội_dung, action_url, btn_text, btn_class)` | Định nghĩa modal rồi mở bằng nút `data-bs-toggle="modal" data-bs-target="#id"`; modal tự có `csrf_token` |

Hàng vượt ngưỡng vắng: thêm class `row-over-threshold` vào `<tr>` (tô đỏ, Mục 7.2).

Menu trái trỏ tới các đường dẫn trong `docs/api_contract.md`; route nào chưa làm thì bấm vào ra 404 cho đến khi TV tương ứng thêm.

## Phân quyền và CSRF

**Phân quyền:** gắn `role_required` cho **mọi** route (ngoài `/login`):

```python
from app.models.enums import Role
from app.utils.decorators import role_required

@bp.route("/lecturer/classes")
@role_required(Role.LECTURER)
def my_classes(): ...
```

Chưa đăng nhập → chuyển tới `/login?next=<trang>` (đăng nhập xong quay lại trang đó). Sai vai trò → HTTP 403 (trang `errors/403.html`). Một route cho nhiều vai trò: `@role_required(Role.LECTURER, Role.ADMIN)`. Lấy người dùng hiện tại bằng `current_user` (Flask-Login).

**CSRF (Flask-WTF, bật cho mọi POST):**
- Mọi `<form method="POST">` phải có dòng này, nếu thiếu server trả 400:
  ```html
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  ```
- Gọi POST bằng JavaScript (fetch/AJAX): lấy token một lần rồi gửi trong header `X-CSRFToken`:
  ```html
  <meta name="csrf-token" content="{{ csrf_token() }}">
  ```
  ```js
  fetch(url, {method: "POST", headers: {"X-CSRFToken": document.querySelector('meta[name=csrf-token]').content}});
  ```
- Đăng xuất là POST (nút trong `base.html` đã có token).
- Trong test, tắt CSRF bằng `WTF_CSRF_ENABLED = False` (xem `tests/test_auth.py`).