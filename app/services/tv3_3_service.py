
"""TV3-3 services: UC8, UC9 and UC10."""

from datetime import date, datetime
from io import BytesIO

from sqlalchemy.exc import IntegrityError

from app.errors import (
    LEAVE_ALREADY_DECIDED,
    NOT_FOUND,
    NOT_OWNER_SECTION,
    ServiceError,
    VALIDATION_ERROR,
)

from app.extensions import db

from app.models import (
    Attendance,
    AttendanceLog,
    AttendanceStatus,
    CheckInMethod,
    ClassSection,
    ClassSession,
    Course,
    Enrollment,
    LeaveRequest,
    LeaveStatus,
    Student,
)


class LeaveService:
    """UC8 - Leave request approval."""

    @staticmethod
    def list_requests(lecturer_id, status=None):

        query = (
            LeaveRequest.query
            .join(
                ClassSession,
                LeaveRequest.session_id == ClassSession.id
            )
            .join(
                ClassSection,
                ClassSession.section_id == ClassSection.id
            )
            .filter(
                ClassSection.lecturer_id == lecturer_id
            )
        )

        if status:
            try:
                status = LeaveStatus[str(status).upper()]
            except KeyError:
                raise ServiceError(
                    VALIDATION_ERROR,
                    "Invalid leave status."
                )

            query = query.filter(
                LeaveRequest.status == status
            )

        return query.order_by(
            LeaveRequest.created_at.desc()
        ).all()

    @staticmethod
    def review(lecturer_id, leave_id, approve):

        leave = db.session.get(
            LeaveRequest,
            int(leave_id)
        )

        if leave is None:
            raise ServiceError(
                NOT_FOUND,
                "Leave request was not found.",
                404
            )

        section = leave.session.section

        if section.lecturer_id != lecturer_id:
            raise ServiceError(
                NOT_OWNER_SECTION,
                "You are not responsible for this class section.",
                403
            )

        if leave.status != LeaveStatus.PENDING:
            raise ServiceError(
                LEAVE_ALREADY_DECIDED,
                "This leave request has already been processed.",
                409
            )

        try:

            leave.status = (
                LeaveStatus.APPROVED
                if approve
                else LeaveStatus.REJECTED
            )

            leave.reviewed_by = lecturer_id
            leave.reviewed_at = datetime.utcnow()

            if approve:

                attendance = Attendance.query.filter_by(
                    session_id=leave.session_id,
                    student_id=leave.student_id
                ).first()

                if attendance is None:

                    attendance = Attendance(
                        session_id=leave.session_id,
                        student_id=leave.student_id,
                        status=AttendanceStatus.EXCUSED,
                        method=CheckInMethod.MANUAL
                    )

                    db.session.add(attendance)

                elif attendance.status != AttendanceStatus.EXCUSED:

                    db.session.add(
                        AttendanceLog(
                            attendance=attendance,
                            changed_by=lecturer_id,
                            old_status=attendance.status,
                            new_status=AttendanceStatus.EXCUSED,
                            reason="Approved leave request"
                        )
                    )

                    attendance.status = AttendanceStatus.EXCUSED

            db.session.commit()

        except IntegrityError as exc:

            db.session.rollback()

            raise ServiceError(
                LEAVE_ALREADY_DECIDED,
                "This request was processed by another user.",
                409
            ) from exc

        except Exception:

            db.session.rollback()
            raise

        return leave

    @staticmethod
    def approve(lecturer_id, leave_id):

        return LeaveService.review(
            lecturer_id,
            leave_id,
            True
        )

    @staticmethod
    def reject(lecturer_id, leave_id):

        return LeaveService.review(
            lecturer_id,
            leave_id,
            False
        )


class ReportService:
    """UC9 - Attendance reports and statistics."""

    @staticmethod
    def _parse_date(value, field_name):

        if not value:
            return None

        try:
            return date.fromisoformat(value)

        except (TypeError, ValueError) as exc:

            raise ServiceError(
                VALIDATION_ERROR,
                f"Invalid {field_name}. Use YYYY-MM-DD."
            ) from exc

    @staticmethod
    def _scope_query(user, filters):

        role = (
            user.role.value
            if hasattr(user.role, "value")
            else str(user.role)
        )

        query = ClassSection.query.join(
            Course,
            ClassSection.course_id == Course.id
        )

        if role == "LECTURER":

            query = query.filter(
                ClassSection.lecturer_id == user.id
            )

        elif role != "ADMIN":

            raise ServiceError(
                "FORBIDDEN",
                "You are not allowed to view reports.",
                403
            )

        if filters.get("semester"):
            query = query.filter(
                ClassSection.semester == filters["semester"]
            )

        if filters.get("course_id"):
            query = query.filter(
                ClassSection.course_id == int(filters["course_id"])
            )

        if filters.get("section_id"):
            query = query.filter(
                ClassSection.id == int(filters["section_id"])
            )

        return query.order_by(
            ClassSection.semester.desc(),
            Course.code,
            ClassSection.id
        )

    @staticmethod
    def filter_options(user):

        sections = ReportService._scope_query(
            user, {}
        ).all()

        courses = {
            section.course.id: section.course
            for section in sections
        }

        semesters = sorted(
            {section.semester for section in sections},
            reverse=True
        )

        return {
            "sections": sections,
            "courses": sorted(
                courses.values(),
                key=lambda course: course.code
            ),
            "semesters": semesters
        }

    @staticmethod
    def generate(user, filters=None):

        filters = filters or {}

        date_from = ReportService._parse_date(
            filters.get("date_from"),
            "start date"
        )

        date_to = ReportService._parse_date(
            filters.get("date_to"),
            "end date"
        )

        if date_from and date_to and date_from > date_to:
            raise ServiceError(
                VALIDATION_ERROR,
                "Start date must not be after end date."
            )

        sections = ReportService._scope_query(
            user,
            filters
        ).all()

        report_rows = []

        for section in sections:

            sessions_query = ClassSession.query.filter(
                ClassSession.section_id == section.id
            )

            if date_from:
                sessions_query = sessions_query.filter(
                    ClassSession.session_date >= date_from
                )

            if date_to:
                sessions_query = sessions_query.filter(
                    ClassSession.session_date <= date_to
                )

            # Exclude future sessions.
            sessions_query = sessions_query.filter(
                ClassSession.session_date <= date.today()
            )

            sessions = sessions_query.order_by(
                ClassSession.session_date,
                ClassSession.start_time
            ).all()

            session_ids = [
                session.id for session in sessions
            ]

            total_sessions = len(session_ids)

            if not session_ids:
                continue

            enrollments = (
                Enrollment.query
                .join(
                    Student,
                    Enrollment.student_id == Student.user_id
                )
                .filter(
                    Enrollment.section_id == section.id
                )
                .order_by(Student.student_code)
                .all()
            )

            attendance_map = {}

            attendances = Attendance.query.filter(
                Attendance.session_id.in_(session_ids)
            ).all()

            for attendance in attendances:

                attendance_map.setdefault(
                    attendance.student_id,
                    []
                ).append(attendance.status)

            for enrollment in enrollments:

                student = enrollment.student

                statuses = attendance_map.get(
                    student.user_id,
                    []
                )

                counts = {
                    "present": sum(
                        s == AttendanceStatus.PRESENT
                        for s in statuses
                    ),

                    "absent": sum(
                        s == AttendanceStatus.ABSENT
                        for s in statuses
                    ),

                    "late": sum(
                        s == AttendanceStatus.LATE
                        for s in statuses
                    ),

                    "excused": sum(
                        s == AttendanceStatus.EXCUSED
                        for s in statuses
                    )
                }

                missing = max(
                    total_sessions - len(statuses),
                    0
                )

                counts["absent"] += missing

                attended = (
                    counts["present"]
                    + counts["late"]
                    + counts["excused"]
                )

                attendance_rate = (
                    attended / total_sessions * 100
                )

                absence_rate = (
                    counts["absent"] / total_sessions * 100
                )

                report_rows.append({

                    "student_id": student.user_id,

                    "student_code": student.student_code,

                    "student_name": student.full_name,

                    "course_code": section.course.code,

                    "course_name": section.course.name,

                    "section_id": section.id,

                    "semester": section.semester,

                    "total_sessions": total_sessions,

                    **counts,

                    "attendance_rate": round(
                        attendance_rate, 2
                    ),

                    "absence_rate": round(
                        absence_rate, 2
                    ),

                    "over_threshold": absence_rate > 20.0

                })

        if filters.get("student_id"):

            try:
                selected_student = int(
                    filters["student_id"]
                )

            except (TypeError, ValueError) as exc:

                raise ServiceError(
                    VALIDATION_ERROR,
                    "Invalid student ID."
                ) from exc

            report_rows = [
                row for row in report_rows
                if row["student_id"] == selected_student
            ]

        summary = {

            "students": len(report_rows),

            "sessions": sum(
                row["total_sessions"]
                for row in report_rows
            ),

            "over_threshold": sum(
                row["over_threshold"]
                for row in report_rows
            )

        }

        return {

            "generated_at": datetime.now(),

            "filters": filters,

            "rows": report_rows,

            "summary": summary

        }

    @staticmethod
    def export_excel(report, output_path=None):

        from openpyxl import Workbook

        from openpyxl.styles import (
            Font,
            PatternFill,
            Alignment
        )

        from openpyxl.utils import get_column_letter

        workbook = Workbook()

        sheet = workbook.active

        sheet.title = "Attendance Report"

        sheet.append([

            "Student ID",
            "Student Name",
            "Course Code",
            "Course Name",
            "Class Section",
            "Semester",
            "Total Sessions",
            "Present",
            "Absent",
            "Late",
            "Excused",
            "Attendance Rate (%)",
            "Absence Rate (%)"

        ])

        for row in report["rows"]:

            sheet.append([

                row["student_code"],
                row["student_name"],
                row["course_code"],
                row["course_name"],
                row["section_id"],
                row["semester"],
                row["total_sessions"],
                row["present"],
                row["absent"],
                row["late"],
                row["excused"],
                row["attendance_rate"],
                row["absence_rate"]

            ])

        for cell in sheet[1]:

            cell.font = Font(
                bold=True,
                color="FFFFFF"
            )

            cell.fill = PatternFill(
                "solid",
                fgColor="245A81"
            )

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center"
            )

        sheet.freeze_panes = "A2"

        sheet.auto_filter.ref = sheet.dimensions

        for column in sheet.columns:

            width = min(
                max(
                    max(
                        len(str(cell.value or ""))
                        for cell in column
                    ) + 2,
                    12
                ),
                32
            )

            sheet.column_dimensions[
                get_column_letter(column[0].column)
            ].width = width

        if output_path:

            workbook.save(output_path)

            return str(output_path)

        stream = BytesIO()

        workbook.save(stream)

        stream.seek(0)

        return stream

    @staticmethod
    def export_pdf(report, output_path=None):

        from reportlab.lib import colors

        from reportlab.lib.enums import TA_CENTER

        from reportlab.lib.pagesizes import (
            A4,
            landscape
        )

        from reportlab.lib.styles import (
            getSampleStyleSheet,
            ParagraphStyle
        )

        from reportlab.lib.units import mm

        from reportlab.pdfbase import pdfmetrics

        from reportlab.pdfbase.ttfonts import TTFont

        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle
        )

        stream = (
            BytesIO()
            if output_path is None
            else output_path
        )

        doc = SimpleDocTemplate(
            stream,
            pagesize=landscape(A4),
            rightMargin=10 * mm,
            leftMargin=10 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm
        )

        styles = getSampleStyleSheet()

        font_name = "Helvetica"

        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arial.ttf",
            __import__("reportlab").__path__[0] + "/fonts/Vera.ttf"
        ]

        for font_path in font_candidates:

            try:

                pdfmetrics.registerFont(
                    TTFont("TV33Unicode", font_path)
                )

                font_name = "TV33Unicode"

                break

            except Exception:
                continue

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName=font_name,
            alignment=TA_CENTER,
            fontSize=16,
            leading=20
        )

        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=7,
            leading=9
        )

        story = [

            Paragraph(
                "STUDENT ATTENDANCE REPORT",
                title_style
            ),

            Spacer(1, 5 * mm),

            Paragraph(
                "Generated at: "
                + report["generated_at"].strftime(
                    "%Y-%m-%d %H:%M"
                ),
                body_style
            ),

            Spacer(1, 3 * mm)

        ]

        headers = [

            "Student ID",
            "Student Name",
            "Course",
            "Class",
            "Semester",
            "Sessions",
            "Present",
            "Absent",
            "Late",
            "Excused",
            "Attendance %",
            "Absence %"

        ]

        data = [headers]

        for row in report["rows"]:

            data.append([

                row["student_code"],
                row["student_name"],
                row["course_code"],
                str(row["section_id"]),
                row["semester"],
                str(row["total_sessions"]),
                str(row["present"]),
                str(row["absent"]),
                str(row["late"]),
                str(row["excused"]),
                f"{row['attendance_rate']:.2f}",
                f"{row['absence_rate']:.2f}"

            ])

        if len(data) == 1:

            data.append(
                ["No data"] + [""] * (len(headers) - 1)
            )

        table = Table(
            data,
            repeatRows=1,
            colWidths=[
                23*mm, 35*mm, 20*mm, 15*mm,
                20*mm, 15*mm, 15*mm, 15*mm,
                13*mm, 15*mm, 22*mm, 20*mm
            ]
        )

        table.setStyle(TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#245A81")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, -1),
                font_name
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.35,
                colors.grey
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#EEF4F8")
                ]
            )

        ]))

        story.append(table)

        doc.build(story)

        if output_path:
            return str(output_path)

        stream.seek(0)

        return stream
