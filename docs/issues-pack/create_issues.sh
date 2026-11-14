#!/usr/bin/env bash
# Tạo nhãn, milestone và toàn bộ Issues bằng GitHub CLI (gh).
# Chạy trong thư mục của repo:
#   DRY_RUN=1 bash /đường/dẫn/create_issues.sh   # chỉ in lệnh, không tạo
#   bash /đường/dẫn/create_issues.sh             # tạo thật
set -uo pipefail

# ---- Điền tên tài khoản GitHub của từng người (không có dấu @) ----
TV1_USER="nguyenhaty51"
TV2_USER="CHANGE_ME"
TV3_USER="CHANGE_ME"
TV4_USER="CHANGE_ME"
TV5_USER="CHANGE_ME"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY="${DRY_RUN:-0}"

run() { if [ "$DRY" = "1" ]; then printf "%q " "$@"; echo; else "$@"; fi; }
assignee() { for u in "$@"; do [ "$u" != "CHANGE_ME" ] && printf "%s," "$u"; done; }

echo "== Tạo nhãn =="
run gh label create "use-case" --color "1D76DB" --force
run gh label create "backend" --color "0E8A16" --force
run gh label create "frontend" --color "FBCA04" --force
run gh label create "foundation" --color "5319E7" --force
run gh label create "integration" --color "C5DEF5" --force
run gh label create "docs" --color "0075CA" --force
run gh label create "bug" --color "B60205" --force

echo "== Tạo milestone =="
run gh api "repos/{owner}/{repo}/milestones" -f title='Ngày 1-2: Nền tảng' -f state=open >/dev/null 2>&1 || true
run gh api "repos/{owner}/{repo}/milestones" -f title='Ngày 3-5: Chức năng' -f state=open >/dev/null 2>&1 || true
run gh api "repos/{owner}/{repo}/milestones" -f title='Ngày 6-7: Ghép nối và hoàn thiện' -f state=open >/dev/null 2>&1 || true

echo "== Tạo Issues =="
A=$(assignee "$TV1_USER" "$TV2_USER" "$TV3_USER" "$TV4_USER" "$TV5_USER"); run gh issue create --title '[S-1] Khởi động nhóm: môi trường, quy tắc, đọc đặc tả' --body-file "$DIR/issues/S-1.md" --label "foundation" --milestone 'Ngày 1-2: Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[TV1-1] Nền tảng: lớp đối tượng theo sơ đồ lớp, cơ sở dữ liệu, dữ liệu mẫu, hợp đồng' --body-file "$DIR/issues/TV1-1.md" --label "foundation,backend" --milestone 'Ngày 1-2: Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[TV1-2] Đăng nhập, phân quyền, đổi mật khẩu (UC1, UC14) và layout chung' --body-file "$DIR/issues/TV1-2.md" --label "use-case,backend,frontend" --milestone 'Ngày 1-2: Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[TV1-3] Docker, ghép nhánh cuối, README và chuẩn bị demo' --body-file "$DIR/issues/TV1-3.md" --label "foundation,integration,docs" --milestone 'Ngày 6-7: Ghép nối và hoàn thiện' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[TV2-1] Phiên QR/PIN (UC6) và điểm danh bằng mã (UC3) – backend' --body-file "$DIR/issues/TV2-1.md" --label "use-case,backend" --milestone 'Ngày 3-5: Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[TV2-2] Điểm danh thủ công (UC5) và sửa điểm danh (UC7) – backend' --body-file "$DIR/issues/TV2-2.md" --label "use-case,backend" --milestone 'Ngày 3-5: Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[TV2-3] Cảnh báo vắng quá ngưỡng (UC15) và gửi đơn xin nghỉ (UC4) – backend' --body-file "$DIR/issues/TV2-3.md" --label "use-case,backend" --milestone 'Ngày 3-5: Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[TV3-1] Quản lý người dùng (UC11) – backend' --body-file "$DIR/issues/TV3-1.md" --label "use-case,backend" --milestone 'Ngày 3-5: Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[TV3-2] Lớp học phần, sinh viên của lớp, nhập Excel, buổi học, xem lớp giảng dạy (UC12, UC13, UC16) – backend' --body-file "$DIR/issues/TV3-2.md" --label "use-case,backend" --milestone 'Ngày 3-5: Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[TV3-3] Duyệt đơn nghỉ, báo cáo, xuất Excel và PDF (UC8, UC9, UC10) – backend' --body-file "$DIR/issues/TV3-3.md" --label "use-case,backend" --milestone 'Ngày 3-5: Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[TV4-1] Giao diện M01 Đăng nhập, M02 Đổi mật khẩu, M03 Trang chủ sinh viên, M07 Thông báo' --body-file "$DIR/issues/TV4-1.md" --label "frontend" --milestone 'Ngày 3-5: Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[TV4-2] Giao diện M04 Điểm danh bằng mã, M05 Lịch sử điểm danh, M06 Gửi đơn xin nghỉ' --body-file "$DIR/issues/TV4-2.md" --label "frontend" --milestone 'Ngày 3-5: Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[TV4-3] Ghép nối khu sinh viên và hoàn thiện giao diện' --body-file "$DIR/issues/TV4-3.md" --label "frontend,integration" --milestone 'Ngày 6-7: Ghép nối và hoàn thiện' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[TV5-1] Giao diện M08 Lớp giảng dạy, M09 Điểm danh/Sửa, M10 Phiên QR/PIN, M11 Duyệt đơn nghỉ' --body-file "$DIR/issues/TV5-1.md" --label "frontend" --milestone 'Ngày 3-5: Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[TV5-2] Giao diện M12 Báo cáo, M13 Quản lý người dùng, M14 Quản lý lớp học phần, M15 Quản lý buổi học' --body-file "$DIR/issues/TV5-2.md" --label "frontend" --milestone 'Ngày 3-5: Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[TV5-3] Ghép nối khu giảng viên, quản trị và hoàn thiện giao diện' --body-file "$DIR/issues/TV5-3.md" --label "frontend,integration" --milestone 'Ngày 6-7: Ghép nối và hoàn thiện' ${A:+--assignee "${A%,}"}

echo "Xong. Kiểm tra tab Issues trên GitHub."
