# Danh sách Issues theo thành viên

Tổng cộng **53** Issues. Mỗi Issue có việc cần làm, tiêu chí hoàn thành, phụ thuộc và tên nhánh; nội dung đầy đủ nằm trong thư mục `issues/`.

Quy ước kích thước: S nửa ngày, M một ngày, L hai ngày trở lên. Milestone: M0 Thiết lập, M1 Nền tảng, M2 Chức năng, M3 Ghép nối và kiểm thử, M4 Hoàn thiện và demo.

Lưu ý: UC4 (Gửi đơn xin nghỉ) chưa có trong bảng chia việc trước đó, nên được gán cho TV2 (Issue T2-7). Đổi người nếu nhóm thấy khác.

## TV1 – Nền tảng, cơ sở dữ liệu, đăng nhập, kiểm thử, triển khai

| Công việc | Size | Milestone | Phụ thuộc |
|---|---|---|---|
| [S-1] Thiết lập GitHub: bảo vệ nhánh, nhãn, milestone, bảng Projects | S | M0 - Thiết lập | — |
| [S-3] Chốt hợp đồng frontend–backend (docs/api_contract.md) | M | M0 - Thiết lập | S-2 |
| [T1-1] Models SQLAlchemy cho 11 bảng theo ERD | L | M1 - Nền tảng | S-2 |
| [T1-2] Migration khởi tạo CSDL (Flask-Migrate) | S | M1 - Nền tảng | T1-1 |
| [T1-3] Script dữ liệu mẫu (scripts/seed.py) | M | M1 - Nền tảng | T1-2 |
| [T1-4][UC1] Đăng nhập, đăng xuất và phân quyền (backend) | M | M1 - Nền tảng | T1-1, T1-3 |
| [T1-5][UC14] Đổi mật khẩu (backend) | S | M1 - Nền tảng | T1-4 |
| [T1-6] Layout chung, menu theo vai trò, CSS dùng chung | M | M1 - Nền tảng | S-3 |
| [T1-7] Docker: chạy ứng dụng và MySQL bằng docker compose | M | M2 - Chức năng | T1-2 |
| [T1-8] Bảng test case (docs/test_cases.xlsx) và quy trình báo lỗi | M | M1 - Nền tảng | S-2 |
| [T1-9] Hạ tầng kiểm thử: fixtures pytest và coverage | S | M1 - Nền tảng | T1-3 |
| [I-6] Kiểm tra yêu cầu phi chức năng | M | M3 - Ghép nối và kiểm thử | I-1, I-2, I-3 |
| [I-7] Chuẩn bị demo, README và nộp bài | M | M4 - Hoàn thiện và demo | I-5 |

## TV2 – Backend 1: điểm danh, mã QR/PIN, cảnh báo, đơn xin nghỉ

| Công việc | Size | Milestone | Phụ thuộc |
|---|---|---|---|
| [T2-1][UC6/UC3] Dịch vụ sinh và kiểm tra mã PIN | S | M2 - Chức năng | T1-1 |
| [T2-2][UC6] Tạo phiên QR/PIN (backend) | M | M2 - Chức năng | T2-1, T1-4 |
| [T2-3][UC5] Điểm danh thủ công (backend) | L | M2 - Chức năng | T2-1, T1-4 |
| [T2-4][UC3] Điểm danh bằng mã (backend) | L | M2 - Chức năng | T2-1, T1-4 |
| [T2-5][UC7] Sửa điểm danh và lưu lịch sử (backend) | M | M2 - Chức năng | T2-3 |
| [T2-6][UC15] Tính tỷ lệ vắng và tạo cảnh báo (backend) | M | M2 - Chức năng | T1-1 |
| [T2-7][UC4] Gửi đơn xin nghỉ (backend) | M | M2 - Chức năng | T1-4 |
| [T2-8] Unit test cho module điểm danh | M | M2 - Chức năng | T2-2..T2-7 |

## TV3 – Backend 2: quản lý, duyệt đơn, báo cáo

| Công việc | Size | Milestone | Phụ thuộc |
|---|---|---|---|
| [T3-1][UC16] Xem lớp giảng dạy (backend) | M | M2 - Chức năng | T1-3 |
| [T3-2][UC11] Quản lý người dùng (backend) | L | M2 - Chức năng | T1-4 |
| [T3-3][UC12] Quản lý môn học và lớp học phần (backend) | M | M2 - Chức năng | T1-4 |
| [T3-4][UC12] Sinh viên của lớp và nhập từ Excel (backend) | M | M2 - Chức năng | T3-3 |
| [T3-5][UC13] Quản lý buổi học (backend) | M | M2 - Chức năng | T3-3 |
| [T3-6][UC8] Duyệt đơn xin nghỉ (backend) | M | M2 - Chức năng | T2-7, T2-6 |
| [T3-7][UC9] Báo cáo và thống kê (backend) | L | M2 - Chức năng | T1-3 |
| [T3-8][UC10] Xuất báo cáo Excel và PDF (backend) | M | M2 - Chức năng | T3-7 |
| [T3-9] Unit test cho module quản lý, đơn nghỉ và báo cáo | M | M2 - Chức năng | T3-1..T3-8 |

## TV4 – Frontend 1: màn hình M01–M07 (sinh viên, đăng nhập)

| Công việc | Size | Milestone | Phụ thuộc |
|---|---|---|---|
| [T4-1][M01] Màn hình Đăng nhập | S | M2 - Chức năng | T1-6, S-3 |
| [T4-2][M02] Màn hình Đổi mật khẩu | S | M2 - Chức năng | T1-6, S-3 |
| [T4-3][M03] Trang chủ sinh viên | M | M2 - Chức năng | T1-6, S-3 |
| [T4-4][M04] Màn hình Điểm danh bằng mã (ưu tiên điện thoại) | L | M2 - Chức năng | T1-6, S-3 |
| [T4-5][M05] Lịch sử điểm danh | M | M2 - Chức năng | T1-6, S-3 |
| [T4-6][M06] Gửi đơn xin nghỉ | M | M2 - Chức năng | T1-6, S-3 |
| [T4-7][M07] Thông báo | S | M2 - Chức năng | T1-6, S-3 |
| [T4-8] Kiểm tra giao diện khu sinh viên | S | M3 - Ghép nối và kiểm thử | T4-1..T4-7 |
| [I-1] Ghép frontend–backend khu sinh viên (M01–M07) | M | M3 - Ghép nối và kiểm thử | T2-2..T2-7, T4-1..T4-7 |

## TV5 – Frontend 2: màn hình M08–M15 (giảng viên, quản trị, báo cáo)

| Công việc | Size | Milestone | Phụ thuộc |
|---|---|---|---|
| [T5-1][M08] Lớp giảng dạy | M | M2 - Chức năng | T1-6, S-3 |
| [T5-2][M09] Điểm danh và Sửa điểm danh | L | M2 - Chức năng | T1-6, S-3 |
| [T5-3][M10] Phiên QR/PIN | M | M2 - Chức năng | T1-6, S-3 |
| [T5-4][M11] Duyệt đơn xin nghỉ | M | M2 - Chức năng | T1-6, S-3 |
| [T5-5][M12] Báo cáo | L | M2 - Chức năng | T1-6, S-3 |
| [T5-6][M13] Quản lý người dùng | L | M2 - Chức năng | T1-6, S-3 |
| [T5-7][M14] Quản lý lớp học phần | L | M2 - Chức năng | T1-6, S-3 |
| [T5-8][M15] Quản lý buổi học | M | M2 - Chức năng | T1-6, S-3 |
| [T5-9] Kiểm tra giao diện khu giảng viên và quản trị | S | M3 - Ghép nối và kiểm thử | T5-1..T5-8 |
| [I-2] Ghép frontend–backend khu giảng viên (M08–M12) | M | M3 - Ghép nối và kiểm thử | T2-2..T2-5, T3-1, T3-6..T3-8, T5-1..T5-5 |
| [I-3] Ghép frontend–backend khu quản trị (M13–M15) | S | M3 - Ghép nối và kiểm thử | T3-2..T3-5, T5-6..T5-8 |

## Việc chung (ALL)

| Công việc | Size | Milestone | Phụ thuộc |
|---|---|---|---|
| [S-2] Mỗi thành viên cài môi trường và mở Pull Request thử | S | M0 - Thiết lập | S-1 |
| [I-4] Kiểm thử hệ thống theo bảng test case | L | M3 - Ghép nối và kiểm thử | I-1, I-2, I-3 |
| [I-5] Sửa lỗi từ kiểm thử | L | M3 - Ghép nối và kiểm thử | I-4 |

## Thứ tự làm gợi ý

1. **Ngày 1–2 (M0):** S-1, S-2, S-3. Trong lúc TV1 làm S-1 và S-3, các thành viên khác làm S-2 và đọc kỹ Mục 4.5 cho use case của mình.
2. **Tuần 1 (M1):** TV1 làm T1-1 đến T1-9 (ưu tiên T1-1, T1-3, T1-4, T1-6, T1-9 vì mọi người phụ thuộc). TV4 và TV5 làm giao diện bằng dữ liệu mẫu. TV2, TV3 làm các hàm không cần chờ nhau (T2-1, T3-1, T3-7).
3. **Tuần 2–3 (M2):** TV2, TV3, TV4, TV5 làm các use case còn lại; mỗi use case một Pull Request.
4. **Tuần 4 (M3):** ghép nối I-1 đến I-3, kiểm thử I-4, sửa lỗi I-5, kiểm tra NFR I-6.
5. **Cuối cùng (M4):** I-7 chuẩn bị demo và nộp bài.
