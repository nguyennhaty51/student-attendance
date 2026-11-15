# Hợp đồng Frontend – Backend (`docs/api_contract.md`)

> **Trạng thái: BẢN ĐỀ XUẤT của TV1 – chờ 4 bạn còn lại duyệt (cuộc họp ngày 1).**
> Sau khi chốt, ai muốn đổi phải mở Pull Request sửa file này (và `app/errors.py` nếu đổi mã lỗi).
> Nguồn: Mục 7.3 (danh sách màn hình), 7.5 (mô tả màn hình), 1.3 (BR1–BR8), 4 (use case) của tài liệu nhóm.
> Đường dẫn/tên trường là **đề xuất của TV1** (tài liệu chỉ mô tả thành phần giao diện, chưa có URL) → cần xác nhận.

Quy ước chung

- Giao diện render phía máy chủ (Flask + Jinja2, kiến trúc MVC Mục 7.1). "Dữ liệu truyền cho trang" = biến đưa vào `render_template`.
- Mọi `POST` có CSRF token (`csrf_token` trong form). Sau `POST` thành công: chuyển hướng (PRG) và `flash("success", ...)`; thất bại: hiển thị lại trang kèm `error_code`, `error_message`.
- Chưa đăng nhập vào trang cần quyền → chuyển tới `/login?next=<url>`. Đã đăng nhập nhưng sai vai trò → HTTP 403, mã `FORBIDDEN`.
- Giờ lưu UTC trong CSDL, hiển thị theo giờ địa phương. Danh sách dài phân trang: `?page=1`, 20 dòng/trang (`page`, `pages`, `total` trong dữ liệu trang).
- Trạng thái điểm danh: `PRESENT | ABSENT | LATE | EXCUSED`; phương thức: `MANUAL | QR_PIN`; đơn nghỉ: `PENDING | APPROVED | REJECTED`.
- `attendance_rate` = (PRESENT + LATE + EXCUSED) / số buổi đã diễn ra; `absence_rate` = ABSENT / số buổi đã diễn ra (BR7); ngưỡng cảnh báo mặc định 20%. Kiểu số: tỷ lệ 0..1 (view tự định dạng %).

## 1. Hợp đồng theo màn hình (M01–M15)

### Chung (M01, M02)

| Màn | Đường dẫn | Phương thức | Vai trò | Dữ liệu backend truyền cho trang | Trường form gửi lên |
|---|---|---|---|---|---|
| M01 Đăng nhập | `/login` | GET, POST | Công khai | `next`, `error_code`, `error_message` | `username`, `password` |
| (đăng xuất) | `/logout` | POST | Mọi vai trò | – (chuyển về `/login`) | – |
| M02 Đổi mật khẩu | `/account/password` | GET, POST | Mọi vai trò | `error_code`, `error_message` | `old_password`, `new_password` (≥ 6 ký tự), `confirm_password` |

Sau đăng nhập thành công: Student → `/student/home` (M03); Lecturer → `/lecturer/classes` (M08); Admin → `/admin/users` (M13).

### Sinh viên (M03–M07)

| Màn | Đường dẫn | Phương thức | Vai trò | Dữ liệu backend truyền cho trang | Trường form gửi lên |
|---|---|---|---|---|---|
| M03 Trang chủ SV | `/student/home` | GET | Student | `courses[]` = `{section_id, course_code, course_name, section_label, lecturer_name, held, present, absent, late, excused, attendance_rate, absence_rate, over_threshold}`; `unread_warnings` (số); `threshold` | – |
| M04 Điểm danh bằng mã | `/student/check-in` | GET, POST | Student | GET: –. POST: `result` = `{ok, message, error_code?, course_name?, session_date?}` | `code` (PIN 6 chữ số; QR chứa đúng chuỗi PIN) |
| M05 Lịch sử điểm danh | `/student/history?section_id=<id>` | GET | Student | `courses[]` (cho dropdown: `{section_id, label}`), `selected_section_id`, `rows[]` = `{session_id, session_date, start_time, end_time, status, note}`, `summary` = `{present, absent, late, excused, attendance_rate}` | `section_id` (query) |
| M06 Xin nghỉ | `/student/leave` | GET, POST | Student | `upcoming_sessions[]` = `{session_id, label}`; `my_requests[]` = `{id, session_label, reason, created_at, status}`; lỗi như trên | `session_id`, `reason` (bắt buộc, ≤ 255 ký tự) |
| M07 Thông báo | `/student/notifications` | GET | Student | `notifications[]` = `{id, message, is_read, created_at}` (mới nhất trước) | – |
| (đánh dấu đã đọc) | `/student/notifications/<id>/read` | POST | Student | – (chuyển về M07) | – |

### Giảng viên (M08–M11)

| Màn | Đường dẫn | Phương thức | Vai trò | Dữ liệu backend truyền cho trang | Trường form gửi lên |
|---|---|---|---|---|---|
| M08 Lớp của tôi | `/lecturer/classes?semester=<s>` | GET | Lecturer | `semesters[]`, `selected_semester`, `classes[]` = `{section_id, course_code, course_name, room, student_count, held, total_sessions}` | `semester` (query) |
| M08 (mở danh sách buổi) | `/lecturer/classes/<section_id>/sessions` | GET | Lecturer (đúng lớp – BR4) | như trên + `sessions[]` = `{session_id, session_date, start_time, end_time, attendance_taken}` | – |
| M09 Điểm danh / Sửa | `/lecturer/sessions/<session_id>/attendance` | GET, POST | Lecturer (đúng lớp) | `session` = `{id, section_id, course_name, session_date, start_time, end_time}`; `students[]` = `{student_id, student_code, full_name, attendance_id?, status?, method?, note}`; `has_saved` (đã có dữ liệu → sửa phải kèm lý do) | Mỗi dòng: `status[<student_id>]` ∈ 4 trạng thái, `note[<student_id>]`, `reason[<student_id>]` (bắt buộc nếu dòng đã lưu bị đổi – BR6). "Mark all Present" chạy ở trình duyệt (JS), chỉ đặt radio |
| M10 Phiên QR/PIN | `/lecturer/sessions/<session_id>/qr-pin` | GET | Lecturer (đúng lớp) | `session`, `active` (bool), `code?`, `qr_payload?` (= `code`), `expires_at?`, `remaining_seconds?`, `checked_in_count`, `lifetime_options` (vd. 3/5/10/15 phút, mặc định 5) | – |
| M10 mở phiên | `/lecturer/sessions/<session_id>/qr-pin/open` | POST | Lecturer (đúng lớp) | – (chuyển về GET) | `minutes` (nguyên, mặc định 5) |
| M10 đóng phiên | `/lecturer/sessions/<session_id>/qr-pin/close` | POST | Lecturer (đúng lớp) | – | – |
| M10 làm mới số liệu | `/lecturer/sessions/<session_id>/qr-pin/status` | GET (JSON) | Lecturer (đúng lớp) | `{active, remaining_seconds, checked_in_count}` | – |
| M11 Duyệt đơn nghỉ | `/lecturer/leave?status=<s>&page=<n>` | GET | Lecturer | `status_filter` (mặc định `PENDING`), `requests[]` = `{id, student_code, student_name, session_label, reason, created_at, status}`, `page`, `pages` | `status`, `page` (query) |
| M11 duyệt / từ chối | `/lecturer/leave/<id>/approve`, `/lecturer/leave/<id>/reject` | POST | Lecturer (đúng lớp) | – | – |

### Báo cáo (M12)

| Màn | Đường dẫn | Phương thức | Vai trò | Dữ liệu backend truyền cho trang | Trường form gửi lên |
|---|---|---|---|---|---|
| M12 Báo cáo | `/reports?semester=&course_id=&section_id=&date_from=&date_to=` | GET | Lecturer (chỉ lớp mình), Admin (tất cả) | `filter_options` = `{semesters[], courses[], sections[]}`; `filters` (giá trị đang chọn); `rows[]` = `{student_code, full_name, present, absent, late, excused, attendance_rate, over_threshold}`; `threshold` | các tham số lọc ở query; có `section_id` thì mới ra bảng |
| M12 Xuất file | `/reports/export?format=xlsx\|pdf&<cùng bộ lọc>` | GET | như trên | Trả về file tải xuống (`.xlsx` / `.pdf`) | – |

### Quản trị (M13–M15)

| Màn | Đường dẫn | Phương thức | Vai trò | Dữ liệu backend truyền cho trang | Trường form gửi lên |
|---|---|---|---|---|---|
| M13 Quản lý người dùng | `/admin/users?q=&role=&page=` | GET | Admin | `users[]` = `{id, username, full_name, role, code, is_active}`, `page`, `pages`, `q`, `role_filter` | `q`, `role` (query) |
| M13 thêm | `/admin/users` | POST | Admin | – | `role` (STUDENT/LECTURER), `username`, `full_name`, `email`, `code` (mã SV/GV), `class_name` (SV) hoặc `department` (GV) |
| M13 sửa | `/admin/users/<id>/edit` | POST | Admin | – | `full_name`, `email`, `class_name`/`department` |
| M13 khóa / mở / đặt lại | `/admin/users/<id>/lock`, `/unlock`, `/reset-password` | POST | Admin | Đặt lại: `temp_password` hiển thị đúng một lần | – |
| M14 Quản lý lớp học phần | `/admin/sections?semester=` | GET | Admin | `sections[]` = `{id, course_code, course_name, semester, room, lecturer_name, student_count}`; `courses[]`, `lecturers[]` (cho form); `students` của lớp đang chọn: `{student_id, student_code, full_name, has_attendance}`; `import_result?` = `{ok_rows, error_rows[{row, message}]}` | `semester` (query) |
| M14 thêm lớp | `/admin/sections` | POST | Admin | – | `course_id`, `semester`, `room`, `lecturer_id` |
| M14 thêm SV | `/admin/sections/<id>/students` | POST | Admin | – | `student_code` |
| M14 nhập Excel | `/admin/sections/<id>/students/import` | POST (multipart) | Admin | – | `file` (.xlsx; cột 1 = mã sinh viên) |
| M14 gỡ SV | `/admin/sections/<id>/students/<student_id>/remove` | POST | Admin | – (lỗi `STUDENT_HAS_ATTENDANCE` nếu đã có điểm danh) | – |
| M15 Quản lý buổi học | `/admin/sessions?section_id=<id>` | GET | Admin | `sections[]` (dropdown), `selected_section_id`, `sessions[]` = `{id, session_date, start_time, end_time, has_attendance}` | `section_id` (query) |
| M15 thêm 1 buổi | `/admin/sessions` | POST | Admin | – | `section_id`, `session_date`, `start_time`, `end_time` |
| M15 thêm theo tuần | `/admin/sessions/weekly` | POST | Admin | – | `section_id`, `start_date`, `weekday` (0–6), `start_time`, `end_time`, `count` |
| M15 sửa / xóa | `/admin/sessions/<id>/edit`, `/admin/sessions/<id>/delete` | POST | Admin | – (lỗi `SESSION_HAS_ATTENDANCE` nếu đã có điểm danh) | như thêm (sửa) |

## 2. Chữ ký phương thức dùng chung (tầng service)

Controller gọi các hàm dưới đây; service ném `app.errors.ServiceError(code, message)` khi lỗi nghiệp vụ.
`*_id` là số nguyên. Hàm ghi dữ liệu chạy trong **một transaction** (NFR3): lỗi thì rollback toàn bộ.
Tên phương thức trên lớp model (README, bảng ánh xạ) chỉ là vỏ; logic nằm ở service.

| Chức năng | Chữ ký | Trả về | Mã lỗi có thể ném |
|---|---|---|---|
| Đăng nhập (UC1) | `AuthService.login(username: str, password: str)` | `User` | `AUTH_INVALID_CREDENTIALS`, `AUTH_ACCOUNT_LOCKED` |
| Đăng xuất (UC1) | `AuthService.logout()` | `None` | – |
| Đổi mật khẩu (UC14) | `AuthService.change_password(user_id, old_password, new_password, confirm_password)` | `None` | `AUTH_WRONG_OLD_PASSWORD`, `VALIDATION_ERROR` |
| Điểm danh cả buổi (UC5) | `AttendanceService.take_attendance(lecturer_id, session_id, records: list[{student_id, status, note}])` | `list[Attendance]` (tạo mới hoặc cập nhật; đổi bản ghi đã lưu thì ghi `AttendanceLog`) | `NOT_OWNER_SECTION`, `NOT_ENROLLED`, `REASON_REQUIRED`, `VALIDATION_ERROR` |
| Sửa điểm danh (UC7) | `AttendanceService.edit_attendance(lecturer_id, attendance_id, new_status, reason)` | `AttendanceLog` | `NOT_OWNER_SECTION`, `REASON_REQUIRED`, `NOT_FOUND` |
| Mở phiên mã (UC6) | `AttendanceService.open_check_in_session(lecturer_id, session_id, minutes=5)` | `{code: str, expires_at: datetime}` | `NOT_OWNER_SECTION`, `VALIDATION_ERROR` |
| Đóng phiên mã (UC6) | `AttendanceService.close_check_in_session(lecturer_id, session_id)` | `None` | `NOT_OWNER_SECTION` |
| Check-in (UC3) – `Student.check_in(code)` | `AttendanceService.check_in(student_id, code: str)` | `Attendance` (PRESENT, `QR_PIN`, `check_in_time`) | `CHECKIN_WRONG_CODE`, `CHECKIN_EXPIRED`, `NOT_ENROLLED`, `CHECKIN_ALREADY`, `CHECKIN_TOO_MANY_ATTEMPTS` |
| Kiểm tra ngưỡng vắng (UC15) | `AttendanceService.check_absence_threshold(student_id, section_id)` | `{held, absent, absence_rate, exceeded: bool, notification_id: int \| None}` – tự gọi sau mỗi lần lưu/sửa điểm danh, duyệt đơn; vượt ngưỡng thì tạo `Notification` | – |
| Tỷ lệ điểm danh | `ClassSection.get_attendance_rate(student_id=None)` | `float` 0..1 | – |
| Gửi đơn nghỉ (UC4) | `LeaveService.submit(student_id, session_id, reason)` | `LeaveRequest` (PENDING) | `LEAVE_NOT_IN_CLASS`, `LEAVE_DUPLICATE`, `VALIDATION_ERROR` |
| Duyệt / từ chối đơn (UC8) | `LeaveService.review(lecturer_id, leave_id, approve: bool)` | `LeaveRequest`; duyệt → buổi đó thành `EXCUSED` | `NOT_OWNER_SECTION`, `LEAVE_ALREADY_DECIDED` (BR8), `NOT_FOUND` |
| Đánh dấu đã đọc (UC15) | `NotificationService.mark_as_read(user_id, notification_id)` | `None` | `NOT_FOUND`, `FORBIDDEN` |
| Báo cáo theo lớp (UC9) | `ReportService.generate_by_section(user, section_id, date_from=None, date_to=None)` | `dict` = `{section, threshold, rows[]}` (cùng dạng `rows[]` ở M12) | `NOT_OWNER_SECTION`, `NOT_FOUND` |
| Báo cáo theo sinh viên (UC9) | `ReportService.generate_by_student(user, student_id, section_id=None)` | `dict` tương tự | `FORBIDDEN`, `NOT_FOUND` |
| Xuất Excel / PDF (UC10) | `ReportService.export_excel(report: dict, path: str)`, `ReportService.export_pdf(report: dict, path: str)` | đường dẫn file đã ghi | – |

Ghi chú

- `take_attendance` bảo đảm BR1 ở tầng ứng dụng (tìm bản ghi cũ theo `(session_id, student_id)` rồi cập nhật); CSDL vẫn có UNIQUE để chặn trùng khi có truy cập đồng thời (mã `DUPLICATE_ATTENDANCE`).
- `check_in`: tìm buổi đang có mã khớp trong các lớp sinh viên đã đăng ký; giới hạn số lần nhập sai (NFR10) do TV2 quyết định (đề xuất 5 lần/phút/tài khoản).
- Phiên mã "đang mở" = `check_in_code` khác rỗng và `code_expiry` còn hạn (ERD không có cột trạng thái buổi học).

## 3. Mã lỗi

| Mã | HTTP | Ý nghĩa / thông báo gợi ý (tiếng Việt) |
|---|---|---|
| `AUTH_INVALID_CREDENTIALS` | 401 | Sai tên đăng nhập hoặc mật khẩu |
| `AUTH_ACCOUNT_LOCKED` | 403 | Tài khoản đã bị khóa |
| `AUTH_WRONG_OLD_PASSWORD` | 400 | Mật khẩu cũ không đúng |
| `FORBIDDEN` | 403 | Không có quyền (sai vai trò / dữ liệu của người khác) |
| `NOT_FOUND` | 404 | Không tìm thấy dữ liệu |
| `VALIDATION_ERROR` | 400 | Dữ liệu nhập không hợp lệ (thiếu trường, sai định dạng) |
| `NOT_OWNER_SECTION` | 403 | Giảng viên không được phân công lớp này (BR4) |
| `NOT_ENROLLED` | 400 | Sinh viên chưa đăng ký lớp (BR3) |
| `DUPLICATE_ATTENDANCE` | 409 | Đã có bản ghi điểm danh cho buổi này (BR1) |
| `REASON_REQUIRED` | 400 | Sửa điểm danh phải nhập lý do (BR6) |
| `CHECKIN_WRONG_CODE` | 400 | Mã không đúng |
| `CHECKIN_EXPIRED` | 400 | Mã đã hết hạn hoặc phiên đã đóng (BR5) |
| `CHECKIN_ALREADY` | 409 | Đã điểm danh buổi này |
| `CHECKIN_TOO_MANY_ATTEMPTS` | 429 | Nhập sai quá nhiều lần, thử lại sau |
| `LEAVE_DUPLICATE` | 409 | Đã có đơn xin nghỉ cho buổi này |
| `LEAVE_NOT_IN_CLASS` | 400 | Buổi học không thuộc lớp của sinh viên |
| `LEAVE_ALREADY_DECIDED` | 409 | Đơn đã được duyệt/từ chối, không đổi được (BR8) |
| `SESSION_HAS_ATTENDANCE` | 409 | Buổi đã có dữ liệu điểm danh, không sửa/xóa được |
| `STUDENT_HAS_ATTENDANCE` | 409 | Sinh viên đã có điểm danh, không gỡ khỏi lớp được |
| `DUPLICATE_VALUE` | 409 | Trùng tên đăng nhập / email / mã (môn, SV, GV) |

## 4. Việc cần chốt trong cuộc họp ngày 1

1. Đường dẫn và tên trường form ở mục 1 (đề xuất của TV1).
2. Nội dung QR: đề xuất QR chỉ chứa PIN 6 chữ số; trình duyệt tự vẽ mã QR từ `qr_payload` (backend không sinh ảnh).
3. Giới hạn nhập sai mã (NFR10) và nơi lưu bộ đếm (bộ nhớ hay bảng) – ERD hiện không có bảng cho việc này.
4. Phân công service: TV2 (`AuthService`, `AttendanceService`), TV3 (`LeaveService`, `ReportService`, `NotificationService`, `UserService`, `ClassService`) – điều chỉnh theo phân công thực tế của nhóm.
