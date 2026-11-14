# Danh sách Issues (bản gọn, 1 tuần)

Tổng cộng **16** Issues: 1 Issue chung và 3 Issues cho mỗi người. Mỗi Issue gồm nhiều việc nhỏ có ô tick; nội dung đầy đủ nằm trong thư mục `issues/`.

Không có Issue kiểm thử: phần kiểm thử sẽ thêm sau khi chức năng xong, dùng đúng Testing Document Template của thầy.

## Việc chung

| Công việc | Hạn | Phụ thuộc |
|---|---|---|
| [S-1] Khởi động nhóm: môi trường, quy tắc, đọc đặc tả | Ngày 1 | — |

## TV1 – Nền tảng, đăng nhập, Docker, ghép nhánh

| Công việc | Hạn | Phụ thuộc |
|---|---|---|
| [TV1-1] Nền tảng: lớp đối tượng theo sơ đồ lớp, cơ sở dữ liệu, dữ liệu mẫu, hợp đồng | Hết ngày 2 | S-1 (hợp đồng chốt trong cuộc họp ngày 1) |
| [TV1-2] Đăng nhập, phân quyền, đổi mật khẩu (UC1, UC14) và layout chung | Hết ngày 3 | TV1-1 |
| [TV1-3] Docker, ghép nhánh cuối, README và chuẩn bị demo | Ngày 5-7 | Các Issue chức năng |

## TV2 – Backend: điểm danh, QR/PIN, cảnh báo, đơn xin nghỉ

| Công việc | Hạn | Phụ thuộc |
|---|---|---|
| [TV2-1] Phiên QR/PIN (UC6) và điểm danh bằng mã (UC3) – backend | Hết ngày 4 | TV1-1, TV1-2 |
| [TV2-2] Điểm danh thủ công (UC5) và sửa điểm danh (UC7) – backend | Hết ngày 5 | TV1-1, TV1-2 |
| [TV2-3] Cảnh báo vắng quá ngưỡng (UC15) và gửi đơn xin nghỉ (UC4) – backend | Hết ngày 4 | TV1-1 |

## TV3 – Backend: quản lý, duyệt đơn, báo cáo

| Công việc | Hạn | Phụ thuộc |
|---|---|---|
| [TV3-1] Quản lý người dùng (UC11) – backend | Hết ngày 3 | TV1-1, TV1-2 |
| [TV3-2] Lớp học phần, sinh viên của lớp, nhập Excel, buổi học, xem lớp giảng dạy (UC12, UC13, UC16) – backend | Hết ngày 5 | TV1-1, TV1-2 |
| [TV3-3] Duyệt đơn nghỉ, báo cáo, xuất Excel và PDF (UC8, UC9, UC10) – backend | Hết ngày 6 | TV2-3, TV1-1 |

## TV4 – Frontend: màn hình M01–M07 (sinh viên)

| Công việc | Hạn | Phụ thuộc |
|---|---|---|
| [TV4-1] Giao diện M01 Đăng nhập, M02 Đổi mật khẩu, M03 Trang chủ sinh viên, M07 Thông báo | Hết ngày 4 | TV1-2, S-1 |
| [TV4-2] Giao diện M04 Điểm danh bằng mã, M05 Lịch sử điểm danh, M06 Gửi đơn xin nghỉ | Hết ngày 5 | TV1-2, S-1 |
| [TV4-3] Ghép nối khu sinh viên và hoàn thiện giao diện | Ngày 5-7 | TV2-1, TV2-3, TV4-1, TV4-2 |

## TV5 – Frontend: màn hình M08–M15 (giảng viên, quản trị)

| Công việc | Hạn | Phụ thuộc |
|---|---|---|
| [TV5-1] Giao diện M08 Lớp giảng dạy, M09 Điểm danh/Sửa, M10 Phiên QR/PIN, M11 Duyệt đơn nghỉ | Hết ngày 5 | TV1-2, S-1 |
| [TV5-2] Giao diện M12 Báo cáo, M13 Quản lý người dùng, M14 Quản lý lớp học phần, M15 Quản lý buổi học | Hết ngày 5 | TV1-2, S-1 |
| [TV5-3] Ghép nối khu giảng viên, quản trị và hoàn thiện giao diện | Ngày 5-7 | TV2-1, TV2-2, TV3-1, TV3-2, TV3-3, TV5-1, TV5-2 |

## Lịch một tuần

| Ngày | Việc chính |
|---|---|
| 1 | Cả nhóm làm Issue chung. TV1 làm lớp đối tượng và hợp đồng frontend–backend; họp cuối ngày chốt hợp đồng. |
| 2 | TV1 xong cơ sở dữ liệu, dữ liệu mẫu và bắt đầu đăng nhập; TV4, TV5 làm giao diện bằng dữ liệu mẫu; TV2, TV3 bắt đầu backend. |
| 3 | TV1 xong đăng nhập và layout chung; TV3 xong quản lý người dùng. |
| 4 | TV2 xong phiên QR/PIN, điểm danh bằng mã, cảnh báo, đơn xin nghỉ; TV4 xong M01–M03, M07. |
| 5 | TV2 xong điểm danh thủ công và sửa; TV3 xong lớp, buổi học, xem lớp; TV4, TV5 xong toàn bộ giao diện. Bắt đầu ghép nối. |
| 6 | TV3 xong duyệt đơn, báo cáo, xuất file; ghép nối mọi khu; sửa lỗi chạy thử. |
| 7 | TV1 làm Docker, README, demo, gắn thẻ `v1.0`. Sau đó mới làm kiểm thử theo template của thầy. |

Lưu ý: nếu thầy yêu cầu giao diện desktop thay vì web thì Issue của TV4, TV5 phải đổi lại; hỏi thầy sớm.
