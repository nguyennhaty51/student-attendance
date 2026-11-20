# Kịch bản demo (khoảng 10 phút)

Thứ tự theo Issue TV1-3: sinh viên điểm danh bằng mã → giảng viên mở phiên và sửa điểm danh → quản trị xem báo cáo. Có thêm 2 phần ngắn (cảnh báo vắng, duyệt đơn nghỉ) dùng khi còn thời gian.

## 1. Chuẩn bị (làm trước giờ demo, khoảng 5 phút)

1. Đưa dữ liệu về trạng thái mẫu ban đầu rồi chạy:
   ```bash
   docker compose down -v
   docker compose up --build
   ```
   Đợi log hiện `Booting worker`, mở <http://localhost:5000>.
2. **Chỉ chạy `down -v` + `up` một lần**, ngay trước demo. Đừng chạy thử đủ kịch bản rồi demo tiếp: buổi 7 của lớp S1 chỉ điểm danh được một lần cho mỗi sinh viên (muốn thử lại phải `down -v`).
3. Mở 2 cửa sổ trình duyệt: một cửa sổ thường (sinh viên), một cửa sổ ẩn danh (giảng viên). Cùng một trình duyệt chỉ giữ được một tài khoản đăng nhập.
4. Mở sẵn tab: `http://localhost:5000/login`.

Tài khoản dùng trong demo (mật khẩu: `sv123`, `gv123`, `admin123`):

| Vai trò | Tài khoản | Dùng cho |
|---|---|---|
| Sinh viên | `sv01`, `sv02` | điểm danh bằng mã (lớp S1) |
| Sinh viên | `sv05` | xem cảnh báo vắng 50% |
| Giảng viên | `gv01` | lớp S1: mở phiên, sửa điểm danh, duyệt đơn |
| Quản trị | `admin` | báo cáo |

Mã buổi học (`id`) dùng trong đường dẫn, đúng khi CSDL vừa tạo mới: lớp S1 có id từ 1 đến 10 theo thứ tự buổi 1 đến 10 (buổi 5 → `5`, buổi 7 → `7`, buổi 8 → `8`).

## 2. Phần A – Sinh viên điểm danh bằng mã (UC3)

| Bước | Thao tác | Kết quả mong đợi |
|---|---|---|
| A1 | Cửa sổ thường: đăng nhập `sv01` / `sv123` | Chuyển tới `/student/home`, thấy các môn của sv01 và tỷ lệ điểm danh |
| A2 | Mở `/student/check-in`, nhập mã **`123456`** (phiên mở sẵn của buổi 7, lớp S1), bấm gửi | "Điểm danh thành công." |
| A3 | Nhập lại `123456` | "Bạn đã điểm danh buổi học này rồi." (mỗi buổi một lần – BR1) |
| A4 | Nhập mã sai `000000` | "Mã không đúng hoặc phiên điểm danh đã đóng." Chỉ thử **một lần**: sai 5 lần liên tiếp sẽ bị khóa 5 phút (NFR11) |
| A5 | Mở `/student/history`, chọn lớp S1 (nếu trang có ô chọn lớp) | Buổi 7 hiện **Có mặt**; các buổi 1–6 có trạng thái từ dữ liệu mẫu (sv01 có 2 buổi **Muộn**) |

Nếu A2 báo mã hết hạn: mã mẫu hết hạn 1 ngày sau lần seed gần nhất. Chạy `docker compose restart web` (seed chạy lại và gia hạn mã) rồi thử lại.

## 3. Phần B – Giảng viên mở phiên và sửa điểm danh (UC6, UC5, UC7)

| Bước | Thao tác | Kết quả mong đợi |
|---|---|---|
| B1 | Cửa sổ ẩn danh: đăng nhập `gv01` / `gv123` | Chuyển tới `/lecturer/classes`, thấy lớp Lập trình Python (S1) |
| B2 | Mở `/lecturer/sessions/8/check-in` (buổi 8), bấm **Mở phiên điểm danh** (thời hạn 5 phút) | Hiện **mã PIN 6 số** và **mã QR**, kèm giờ hết hạn (BR5) |
| B3 | Cửa sổ thường (sv01 đã đăng nhập): `/student/check-in`, nhập PIN vừa hiện | "Điểm danh thành công." Làm tương tự với `sv02` nếu muốn thêm một sinh viên (đăng xuất sv01, đăng nhập sv02) |
| B4 | Cửa sổ giảng viên: bấm **Đóng phiên điểm danh** | Phiên đóng. Sinh viên nhập lại mã sẽ báo "phiên điểm danh đã đóng" |
| B5 | Mở `/lecturer/sessions/5/attendance` (buổi 5, đã điểm danh) | Bảng 12 sinh viên với trạng thái đã lưu |
| B6 | Đổi trạng thái của một sinh viên (ví dụ `sv03` từ Có mặt sang Vắng), **để trống** ô "Lý do sửa", bấm **Lưu điểm danh** | Báo lỗi bắt buộc nhập lý do (BR6), chưa lưu |
| B7 | Nhập lý do "Sinh viên xin phép muộn", lưu lại | "Đã lưu điểm danh." |
| B8 | (Cho thấy lịch sử sửa) chạy trong terminal: `docker compose exec db mysql -uattendance -pattendance_pw attendance -e "SELECT attendance_id, old_status, new_status, reason, changed_at FROM attendance_logs"` (nếu đã đổi mật khẩu trong `.env` thì dùng mật khẩu đó) | Có dòng mẫu của sv01 buổi 5 (Vắng → Muộn) và dòng vừa tạo |

Ghi chú: nút **Điểm danh** và **Mở điểm danh QR/PIN** ở trang `/lecturer/classes` luôn dẫn tới buổi đầu tiên của lớp (buổi 1, đã điểm danh xong), nên khi demo vào buổi 5, 7, 8 thì gõ trực tiếp đường dẫn như trên.

## 4. Phần C – Quản trị xem báo cáo (UC9, UC10)

| Bước | Thao tác | Kết quả mong đợi |
|---|---|---|
| C1 | Đăng xuất, đăng nhập `admin` / `admin123` | Chuyển tới `/admin/users`, thấy danh sách người dùng (UC11) |
| C2 | Menu **Báo cáo** (`/reports`): chọn lớp học phần S1 (Lập trình Python), bấm **Xem báo cáo** | Bảng điểm danh từng sinh viên; hàng `sv05` (vắng 3/6 = 50% > 20%) **tô đỏ** (BR7) |
| C3 | Bấm **Xuất Excel**, rồi **Xuất PDF** | Tải về 2 file `.xlsx` và `.pdf` |
| C4 | (Nếu còn thời gian) mở `/admin/sections` và `/admin/sessions` | Danh sách lớp học phần và buổi học (UC12, UC13) |

## 5. Phần bổ sung (tùy chọn)

- **Cảnh báo vắng (UC15):** đăng nhập `sv05` / `sv123` → `/student/home` có dòng "Cảnh báo: tỷ lệ vắng môn INT1001 …"; `/student/notifications` có thông báo cảnh báo.
- **Duyệt đơn nghỉ (UC8):** giảng viên `gv01` → `/lecturer/leave` → đơn của `sv04` (đang chờ) → **Approve**. Đăng nhập `sv04` → `/student/leave` thấy đơn chuyển sang **Đã duyệt**.
- **Phân quyền:** đang là sinh viên, gõ `/admin/users` → trang 403.
- **Giao diện co giãn:** thu nhỏ cửa sổ trình duyệt, menu trái thu gọn thành nút.

## 6. Nếu có sự cố khi demo

| Sự cố | Cách xử lý nhanh |
|---|---|
| Trang không mở được | `docker compose ps` xem 2 dịch vụ `db`, `web` đều `running`; `docker compose logs web` xem lỗi |
| Báo lỗi lạ sau khi đã thử nhiều lần | `docker compose down -v && docker compose up --build`, đợi `Booting worker` |
| Mã `123456` không còn dùng được | Dùng phần B2 (giảng viên mở phiên mới ở buổi 8) để lấy mã mới |
| Quên mật khẩu mẫu | Xem bảng "Tài khoản mẫu" trong `README.md` |
