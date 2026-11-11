#!/usr/bin/env bash
# Tạo nhãn, milestone và toàn bộ Issues bằng GitHub CLI (gh).
# Cách dùng: cài gh, chạy `gh auth login`, vào THƯ MỤC CỦA REPO, sửa tên GitHub bên dưới, rồi chạy:
#   bash /đường/dẫn/create_issues.sh            # tạo thật
#   DRY_RUN=1 bash /đường/dẫn/create_issues.sh  # chỉ in lệnh, không tạo
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
run gh label create "testing" --color "D93F0B" --force
run gh label create "docs" --color "0075CA" --force
run gh label create "integration" --color "C5DEF5" --force
run gh label create "bug" --color "B60205" --force
run gh label create "size:S" --color "EDEDED" --force
run gh label create "size:M" --color "BFD4F2" --force
run gh label create "size:L" --color "7057FF" --force

echo "== Tạo milestone =="
run gh api "repos/{owner}/{repo}/milestones" -f title='M0 - Thiết lập' -f state=open >/dev/null 2>&1 || true
run gh api "repos/{owner}/{repo}/milestones" -f title='M1 - Nền tảng' -f state=open >/dev/null 2>&1 || true
run gh api "repos/{owner}/{repo}/milestones" -f title='M2 - Chức năng' -f state=open >/dev/null 2>&1 || true
run gh api "repos/{owner}/{repo}/milestones" -f title='M3 - Ghép nối và kiểm thử' -f state=open >/dev/null 2>&1 || true
run gh api "repos/{owner}/{repo}/milestones" -f title='M4 - Hoàn thiện và demo' -f state=open >/dev/null 2>&1 || true

echo "== Tạo Issues =="
A=$(assignee "$TV1_USER"); run gh issue create --title '[S-1] Thiết lập GitHub: bảo vệ nhánh, nhãn, milestone, bảng Projects' --body-file "$DIR/issues/S-1.md" --label "foundation,docs,size:S" --milestone 'M0 - Thiết lập' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER" "$TV2_USER" "$TV3_USER" "$TV4_USER" "$TV5_USER"); run gh issue create --title '[S-2] Mỗi thành viên cài môi trường và mở Pull Request thử' --body-file "$DIR/issues/S-2.md" --label "foundation,size:S" --milestone 'M0 - Thiết lập' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[S-3] Chốt hợp đồng frontend–backend (docs/api_contract.md)' --body-file "$DIR/issues/S-3.md" --label "foundation,docs,size:M" --milestone 'M0 - Thiết lập' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[T1-1] Models SQLAlchemy cho 11 bảng theo ERD' --body-file "$DIR/issues/T1-1.md" --label "foundation,backend,size:L" --milestone 'M1 - Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[T1-2] Migration khởi tạo CSDL (Flask-Migrate)' --body-file "$DIR/issues/T1-2.md" --label "foundation,backend,size:S" --milestone 'M1 - Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[T1-3] Script dữ liệu mẫu (scripts/seed.py)' --body-file "$DIR/issues/T1-3.md" --label "foundation,size:M" --milestone 'M1 - Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[T1-4][UC1] Đăng nhập, đăng xuất và phân quyền (backend)' --body-file "$DIR/issues/T1-4.md" --label "use-case,backend,size:M" --milestone 'M1 - Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[T1-5][UC14] Đổi mật khẩu (backend)' --body-file "$DIR/issues/T1-5.md" --label "use-case,backend,size:S" --milestone 'M1 - Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[T1-6] Layout chung, menu theo vai trò, CSS dùng chung' --body-file "$DIR/issues/T1-6.md" --label "foundation,frontend,size:M" --milestone 'M1 - Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[T1-7] Docker: chạy ứng dụng và MySQL bằng docker compose' --body-file "$DIR/issues/T1-7.md" --label "foundation,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[T1-8] Bảng test case (docs/test_cases.xlsx) và quy trình báo lỗi' --body-file "$DIR/issues/T1-8.md" --label "testing,docs,size:M" --milestone 'M1 - Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[T1-9] Hạ tầng kiểm thử: fixtures pytest và coverage' --body-file "$DIR/issues/T1-9.md" --label "testing,foundation,size:S" --milestone 'M1 - Nền tảng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[T2-1][UC6/UC3] Dịch vụ sinh và kiểm tra mã PIN' --body-file "$DIR/issues/T2-1.md" --label "backend,size:S" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[T2-2][UC6] Tạo phiên QR/PIN (backend)' --body-file "$DIR/issues/T2-2.md" --label "use-case,backend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[T2-3][UC5] Điểm danh thủ công (backend)' --body-file "$DIR/issues/T2-3.md" --label "use-case,backend,size:L" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[T2-4][UC3] Điểm danh bằng mã (backend)' --body-file "$DIR/issues/T2-4.md" --label "use-case,backend,size:L" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[T2-5][UC7] Sửa điểm danh và lưu lịch sử (backend)' --body-file "$DIR/issues/T2-5.md" --label "use-case,backend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[T2-6][UC15] Tính tỷ lệ vắng và tạo cảnh báo (backend)' --body-file "$DIR/issues/T2-6.md" --label "use-case,backend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[T2-7][UC4] Gửi đơn xin nghỉ (backend)' --body-file "$DIR/issues/T2-7.md" --label "use-case,backend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV2_USER"); run gh issue create --title '[T2-8] Unit test cho module điểm danh' --body-file "$DIR/issues/T2-8.md" --label "testing,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[T3-1][UC16] Xem lớp giảng dạy (backend)' --body-file "$DIR/issues/T3-1.md" --label "use-case,backend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[T3-2][UC11] Quản lý người dùng (backend)' --body-file "$DIR/issues/T3-2.md" --label "use-case,backend,size:L" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[T3-3][UC12] Quản lý môn học và lớp học phần (backend)' --body-file "$DIR/issues/T3-3.md" --label "use-case,backend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[T3-4][UC12] Sinh viên của lớp và nhập từ Excel (backend)' --body-file "$DIR/issues/T3-4.md" --label "use-case,backend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[T3-5][UC13] Quản lý buổi học (backend)' --body-file "$DIR/issues/T3-5.md" --label "use-case,backend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[T3-6][UC8] Duyệt đơn xin nghỉ (backend)' --body-file "$DIR/issues/T3-6.md" --label "use-case,backend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[T3-7][UC9] Báo cáo và thống kê (backend)' --body-file "$DIR/issues/T3-7.md" --label "use-case,backend,size:L" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[T3-8][UC10] Xuất báo cáo Excel và PDF (backend)' --body-file "$DIR/issues/T3-8.md" --label "use-case,backend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV3_USER"); run gh issue create --title '[T3-9] Unit test cho module quản lý, đơn nghỉ và báo cáo' --body-file "$DIR/issues/T3-9.md" --label "testing,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[T4-1][M01] Màn hình Đăng nhập' --body-file "$DIR/issues/T4-1.md" --label "frontend,size:S" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[T4-2][M02] Màn hình Đổi mật khẩu' --body-file "$DIR/issues/T4-2.md" --label "frontend,size:S" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[T4-3][M03] Trang chủ sinh viên' --body-file "$DIR/issues/T4-3.md" --label "frontend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[T4-4][M04] Màn hình Điểm danh bằng mã (ưu tiên điện thoại)' --body-file "$DIR/issues/T4-4.md" --label "frontend,size:L" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[T4-5][M05] Lịch sử điểm danh' --body-file "$DIR/issues/T4-5.md" --label "frontend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[T4-6][M06] Gửi đơn xin nghỉ' --body-file "$DIR/issues/T4-6.md" --label "frontend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[T4-7][M07] Thông báo' --body-file "$DIR/issues/T4-7.md" --label "frontend,size:S" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[T4-8] Kiểm tra giao diện khu sinh viên' --body-file "$DIR/issues/T4-8.md" --label "testing,frontend,size:S" --milestone 'M3 - Ghép nối và kiểm thử' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[T5-1][M08] Lớp giảng dạy' --body-file "$DIR/issues/T5-1.md" --label "frontend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[T5-2][M09] Điểm danh và Sửa điểm danh' --body-file "$DIR/issues/T5-2.md" --label "frontend,size:L" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[T5-3][M10] Phiên QR/PIN' --body-file "$DIR/issues/T5-3.md" --label "frontend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[T5-4][M11] Duyệt đơn xin nghỉ' --body-file "$DIR/issues/T5-4.md" --label "frontend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[T5-5][M12] Báo cáo' --body-file "$DIR/issues/T5-5.md" --label "frontend,size:L" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[T5-6][M13] Quản lý người dùng' --body-file "$DIR/issues/T5-6.md" --label "frontend,size:L" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[T5-7][M14] Quản lý lớp học phần' --body-file "$DIR/issues/T5-7.md" --label "frontend,size:L" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[T5-8][M15] Quản lý buổi học' --body-file "$DIR/issues/T5-8.md" --label "frontend,size:M" --milestone 'M2 - Chức năng' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[T5-9] Kiểm tra giao diện khu giảng viên và quản trị' --body-file "$DIR/issues/T5-9.md" --label "testing,frontend,size:S" --milestone 'M3 - Ghép nối và kiểm thử' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV4_USER"); run gh issue create --title '[I-1] Ghép frontend–backend khu sinh viên (M01–M07)' --body-file "$DIR/issues/I-1.md" --label "integration,size:M" --milestone 'M3 - Ghép nối và kiểm thử' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[I-2] Ghép frontend–backend khu giảng viên (M08–M12)' --body-file "$DIR/issues/I-2.md" --label "integration,size:M" --milestone 'M3 - Ghép nối và kiểm thử' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV5_USER"); run gh issue create --title '[I-3] Ghép frontend–backend khu quản trị (M13–M15)' --body-file "$DIR/issues/I-3.md" --label "integration,size:S" --milestone 'M3 - Ghép nối và kiểm thử' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER" "$TV2_USER" "$TV3_USER" "$TV4_USER" "$TV5_USER"); run gh issue create --title '[I-4] Kiểm thử hệ thống theo bảng test case' --body-file "$DIR/issues/I-4.md" --label "testing,integration,size:L" --milestone 'M3 - Ghép nối và kiểm thử' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER" "$TV2_USER" "$TV3_USER" "$TV4_USER" "$TV5_USER"); run gh issue create --title '[I-5] Sửa lỗi từ kiểm thử' --body-file "$DIR/issues/I-5.md" --label "bug,integration,size:L" --milestone 'M3 - Ghép nối và kiểm thử' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[I-6] Kiểm tra yêu cầu phi chức năng' --body-file "$DIR/issues/I-6.md" --label "testing,size:M" --milestone 'M3 - Ghép nối và kiểm thử' ${A:+--assignee "${A%,}"}
A=$(assignee "$TV1_USER"); run gh issue create --title '[I-7] Chuẩn bị demo, README và nộp bài' --body-file "$DIR/issues/I-7.md" --label "docs,size:M" --milestone 'M4 - Hoàn thiện và demo' ${A:+--assignee "${A%,}"}

echo "Xong. Kiểm tra tab Issues trên GitHub."
