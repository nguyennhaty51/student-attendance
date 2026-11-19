from datetime import date
from flask import current_app
from app.extensions import db
from app.errors import ServiceError
from app.models.academic import ClassSection, ClassSession
from app.models.attendance import Attendance
from app.models.enums import Role, AttendanceStatus
from app.models.user import Student


class ReportService:
    @staticmethod
    def generate_by_section(user, section_id, date_from=None, date_to=None):
        section = db.session.get(ClassSection, int(section_id))
        if not section:
            raise ServiceError("NOT_FOUND", "Không tìm thấy lớp học phần.", 404)
        if user.role == Role.LECTURER and section.lecturer_id != user.id:
            raise ServiceError("NOT_OWNER_SECTION", "Bạn không được phân công lớp này.", 403)
        if user.role not in (Role.LECTURER, Role.ADMIN):
            raise ServiceError("FORBIDDEN", "Bạn không có quyền xem báo cáo.", 403)

        query = ClassSession.query.filter_by(section_id=section.id).filter(
            ClassSession.session_date <= date.today())
        if date_from:
            query = query.filter(ClassSession.session_date >= date.fromisoformat(date_from))
        if date_to:
            query = query.filter(ClassSession.session_date <= date.fromisoformat(date_to))
        sessions = query.order_by(ClassSession.session_date, ClassSession.start_time).all()
        session_ids = [s.id for s in sessions]
        threshold = float(current_app.config.get('ABSENCE_THRESHOLD', 0.20))
        rows = []
        for enrollment in section.enrollments:
            student = enrollment.student
            records = Attendance.query.filter(
                Attendance.student_id == student.user_id,
                Attendance.session_id.in_(session_ids)
            ).all() if session_ids else []
            counts = {status: 0 for status in AttendanceStatus}
            for record in records:
                counts[record.status] += 1
            held = len(sessions)
            absence_rate = counts[AttendanceStatus.ABSENT] / held if held else 0
            attendance_rate = (counts[AttendanceStatus.PRESENT] + counts[AttendanceStatus.LATE] +
                               counts[AttendanceStatus.EXCUSED]) / held if held else 0
            rows.append({
                "student_code": student.student_code,
                "full_name": student.full_name,
                "present": counts[AttendanceStatus.PRESENT],
                "absent": counts[AttendanceStatus.ABSENT],
                "late": counts[AttendanceStatus.LATE],
                "excused": counts[AttendanceStatus.EXCUSED],
                "attendance_rate": round(attendance_rate, 4),
                "absence_rate": round(absence_rate, 4),
                "over_threshold": absence_rate > threshold and held > 0,
            })
        rows.sort(key=lambda row: row["student_code"])
        return {"section": section, "threshold": threshold, "rows": rows,
                "sessions_count": len(sessions)}

    @staticmethod
    def export_excel(report, path):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        wb = Workbook()
        ws = wb.active
        ws.title = "Bao cao diem danh"
        section = report["section"]
        ws.append(["BÁO CÁO ĐIỂM DANH"])
        ws.append(["Môn học", f"{section.course.code} - {section.course.name}"])
        ws.append(["Học kỳ", section.semester])
        ws.append(["Số buổi", report.get("sessions_count", 0)])
        ws.append(["Ngưỡng vắng", f'{report["threshold"] * 100:.0f}%'])
        ws.append([])
        ws.append(["Mã sinh viên", "Họ và tên", "Có mặt", "Vắng", "Đi muộn",
                   "Có phép", "Tỷ lệ điểm danh", "Cảnh báo"])
        for row in report["rows"]:
            ws.append([row["student_code"], row["full_name"], row["present"],
                       row["absent"], row["late"], row["excused"],
                       f'{row["attendance_rate"] * 100:.2f}%',
                       "Vượt ngưỡng" if row["over_threshold"] else ""])
        for cell in ws[7]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="2457A7")
            cell.alignment = Alignment(horizontal="center")
        ws.freeze_panes = "A8"
        ws.auto_filter.ref = f"A7:H{ws.max_row}"
        for column in ws.columns:
            letter = column[0].column_letter
            ws.column_dimensions[letter].width = min(max(max(len(str(c.value or "")) for c in column) + 2, 12), 36)
        wb.save(path)
        return path

    @staticmethod
    def export_pdf(report, path):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import mm
        section = report["section"]
        doc = SimpleDocTemplate(path, pagesize=landscape(A4), rightMargin=12*mm,
                                leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
        styles = getSampleStyleSheet()
        story = [Paragraph("BAO CAO DIEM DANH", styles["Title"]),
                 Paragraph(f"{section.course.code} - {section.course.name} | Hoc ky: {section.semester}", styles["Normal"]),
                 Paragraph(f"So buoi: {report.get('sessions_count', 0)} | Nguong vang: {report['threshold'] * 100:.0f}%", styles["Normal"]),
                 Spacer(1, 8)]
        data = [["Ma SV", "Ho va ten", "Co mat", "Vang", "Muon", "Co phep", "Ty le", "Canh bao"]]
        for r in report["rows"]:
            data.append([r["student_code"], r["full_name"], r["present"], r["absent"],
                         r["late"], r["excused"], f'{r["attendance_rate"] * 100:.2f}%',
                         "Vuot nguong" if r["over_threshold"] else ""])
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2457A7")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), .4, colors.grey),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F1F5F9")]),
        ]))
        story.append(table)
        doc.build(story)
        return path
