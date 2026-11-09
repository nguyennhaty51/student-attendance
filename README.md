# Student Attendance System

Hệ thống điểm danh sinh viên (đồ án môn học). Tài liệu đặc tả nằm trong thư mục `docs/`.

## Chạy trên máy
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # rồi sửa giá trị trong .env
flask --app app:create_app run --debug
```
Mở http://127.0.0.1:5000

## Chạy kiểm thử
```bash
pytest
```

## Chạy bằng Docker
```bash
cp .env.example .env
docker compose up --build
```

## Cấu trúc thư mục
| Thư mục | Nội dung |
|---|---|
| `app/routes/` | Controller (nhận yêu cầu, gọi service, trả về trang) |
| `app/services/` | Nghiệp vụ (các use case, quy tắc BR1–BR8) |
| `app/repositories/` | Truy cập cơ sở dữ liệu |
| `app/models/` | Lớp ánh xạ 11 bảng của ERD |
| `app/templates/` | Giao diện HTML (M01–M15) |
| `app/static/` | CSS, JavaScript |
| `tests/` | Unit test |
| `migrations/` | Cập nhật cấu trúc cơ sở dữ liệu |
| `scripts/` | Script dữ liệu mẫu |
| `docs/` | Tài liệu đặc tả |

Quy tắc làm việc nhóm: xem [CONTRIBUTING.md](CONTRIBUTING.md).
