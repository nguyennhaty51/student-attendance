# Quy tắc làm việc nhóm

## 1. Nhánh
- `main`: luôn chạy được, chỉ nhận code từ `develop` ở các mốc. Không ai push thẳng.
- `develop`: nhánh ghép chung. Cũng không push thẳng, chỉ nhận Pull Request.
- Nhánh làm việc tách từ `develop`, đặt tên theo kiểu:
  - `feature/uc3-check-in`
  - `fix/uc5-sai-tinh-trang`
  - `docs/cap-nhat-readme`
- Mỗi use case một nhánh. Làm xong thì xóa nhánh sau khi ghép.

## 2. Commit
Viết ngắn, rõ, bằng tiếng Việt hoặc tiếng Anh nhưng thống nhất, có tiền tố:

| Tiền tố | Dùng khi |
|---|---|
| `feat:` | thêm chức năng |
| `fix:` | sửa lỗi |
| `test:` | thêm hoặc sửa test |
| `docs:` | sửa tài liệu |
| `refactor:` | sửa cấu trúc, không đổi chức năng |
| `chore:` | việc lặt vặt (cấu hình, thư viện) |

Ví dụ: `feat: UC3 kiểm tra mã PIN còn hạn`

Commit nhỏ, thường xuyên. Không commit `.env`, mật khẩu, file `.sqlite3`.

## 3. Pull Request
1. Cập nhật nhánh từ `develop` trước khi mở PR: `git pull origin develop` rồi xử lý xung đột.
2. Mở PR vào `develop`, điền mẫu PR, nhắc tới Issue (`Closes #n`).
3. Cần **ít nhất 1 người duyệt** và CI (pytest) phải xanh mới được ghép.
4. Người duyệt xem logic, test và có sửa file của người khác không.
5. Ghép bằng "Squash and merge" để lịch sử gọn.

Vòng duyệt chéo: TV1 duyệt TV2, TV2 duyệt TV3, TV3 duyệt TV4, TV4 duyệt TV5, TV5 duyệt TV1.

## 4. Sở hữu thư mục
| Thành viên | Thư mục |
|---|---|
| TV1 | `app/models/`, `migrations/`, `config.py`, `Dockerfile`, `tests/` chung, `templates/base.html`, `static/css/` |
| TV2 | `services/`, `repositories/`, `routes/` của điểm danh |
| TV3 | `services/`, `repositories/`, `routes/` của người dùng, lớp, buổi học, đơn nghỉ, báo cáo |
| TV4 | `templates/` và `static/` của màn hình M01–M07 |
| TV5 | `templates/` và `static/` của màn hình M08–M15 |

Muốn sửa file của người khác: nhắn chủ thư mục hoặc gửi PR nhỏ cho họ duyệt.

## 5. Xong việc (Definition of Done)
Một use case chỉ được coi là xong khi: chạy được, có unit test qua `pytest`, đã được duyệt và ghép vào `develop`, Issue đã đóng.

## 6. Họp và theo dõi
- Họp 1 lần/tuần, 15–30 phút: ai làm gì, vướng gì.
- Công việc theo dõi bằng GitHub Issues và bảng Projects (Cần làm, Đang làm, Chờ duyệt, Xong).
- Lỗi báo bằng Issue mẫu "Lỗi", ghi mã test case.
