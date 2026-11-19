
"""Business logic for UC12, UC13 and UC16 (TV3-2)."""

from datetime import date, time, timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.errors import (
    DUPLICATE_VALUE,
    NOT_FOUND,
    SESSION_HAS_ATTENDANCE,
    STUDENT_HAS_ATTENDANCE,
    VALIDATION_ERROR,
    ServiceError,
)

from app.extensions import db

from app.models import (
    Attendance,
    ClassSection,
    ClassSession,
    Course,
    Enrollment,
    Lecturer,
    Student,
)


class ClassService:
    """UC12 and UC16 class-related operations."""

    @staticmethod
    def _fail(code, message, status=400):
        raise ServiceError(code, message, status)

    # =====================================================
    # UC12 - MANAGE CLASS SECTIONS
    # =====================================================

    @staticmethod
    def list_sections(semester=None, page=1, per_page=20):
        query = ClassSection.query.join(Course)

        if semester:
            query = query.filter(ClassSection.semester == semester)

        return query.order_by(
            ClassSection.semester.desc(),
            Course.code,
            ClassSection.id
        ).paginate(
            page=max(1, page),
            per_page=min(100, max(1, per_page)),
            error_out=False
        )

    @staticmethod
    def list_courses():
        return Course.query.order_by(Course.code).all()

    @classmethod
    def create_course(cls, code, name, credits):
        code = (code or "").strip()
        name = (name or "").strip()

        try:
            credits = int(credits)
        except (TypeError, ValueError):
            cls._fail(
                VALIDATION_ERROR,
                "Credits must be an integer."
            )

        if (
            not code or not name
            or credits < 1 or credits > 30
            or len(code) > 20 or len(name) > 150
        ):
            cls._fail(
                VALIDATION_ERROR,
                "Invalid course information."
            )

        existing = Course.query.filter(
            func.lower(Course.code) == code.lower()
        ).first()

        if existing:
            cls._fail(
                DUPLICATE_VALUE,
                "Course code already exists.",
                409
            )

        course = Course(
            code=code,
            name=name,
            credits=credits
        )

        db.session.add(course)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            cls._fail(
                DUPLICATE_VALUE,
                "Course code already exists.",
                409
            )

        return course

    @classmethod
    def update_course(cls, course_id, code, name, credits):
        course = db.session.get(Course, course_id)

        if not course:
            cls._fail(NOT_FOUND, "Course not found.", 404)

        code = (code or "").strip()
        name = (name or "").strip()

        try:
            credits = int(credits)
        except (TypeError, ValueError):
            cls._fail(
                VALIDATION_ERROR,
                "Credits must be an integer."
            )

        if (
            not code or not name
            or credits < 1 or credits > 30
            or len(code) > 20 or len(name) > 150
        ):
            cls._fail(
                VALIDATION_ERROR,
                "Invalid course information."
            )

        duplicate = Course.query.filter(
            func.lower(Course.code) == code.lower(),
            Course.id != course_id
        ).first()

        if duplicate:
            cls._fail(
                DUPLICATE_VALUE,
                "Course code already exists.",
                409
            )

        course.code = code
        course.name = name
        course.credits = credits

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            cls._fail(
                DUPLICATE_VALUE,
                "Course code already exists.",
                409
            )

        return course

    @classmethod
    def delete_course(cls, course_id):
        course = db.session.get(Course, course_id)

        if not course:
            cls._fail(NOT_FOUND, "Course not found.", 404)

        if ClassSection.query.filter_by(
            course_id=course_id
        ).first():
            cls._fail(
                VALIDATION_ERROR,
                "Cannot delete a course used by a class section.",
                409
            )

        db.session.delete(course)
        db.session.commit()

    @classmethod
    def create_section(
        cls,
        course_id,
        semester,
        room,
        lecturer_id
    ):
        semester = (semester or "").strip()
        room = (room or "").strip() or None

        if (
            not semester
            or len(semester) > 20
            or len(room or "") > 30
            or not course_id
            or not lecturer_id
        ):
            cls._fail(
                VALIDATION_ERROR,
                "Invalid class section information."
            )

        course = db.session.get(Course, course_id)
        lecturer = db.session.get(Lecturer, lecturer_id)

        if not course or not lecturer:
            cls._fail(
                NOT_FOUND,
                "Course or lecturer not found.",
                404
            )

        section = ClassSection(
            course_id=course.id,
            lecturer_id=lecturer.user_id,
            semester=semester,
            room=room
        )

        db.session.add(section)
        db.session.commit()

        return section

    @classmethod
    def update_section(
        cls,
        section_id,
        course_id,
        semester,
        room,
        lecturer_id
    ):
        section = db.session.get(ClassSection, section_id)

        if not section:
            cls._fail(
                NOT_FOUND,
                "Class section not found.",
                404
            )

        course = db.session.get(Course, course_id)
        lecturer = db.session.get(Lecturer, lecturer_id)

        semester = (semester or "").strip()
        room = (room or "").strip()

        if (
            not course
            or not lecturer
            or not semester
            or len(semester) > 20
            or len(room) > 30
        ):
            cls._fail(
                VALIDATION_ERROR,
                "Invalid class section information."
            )

        section.course_id = course.id
        section.lecturer_id = lecturer.user_id
        section.semester = semester
        section.room = room or None

        db.session.commit()

        return section

    # =====================================================
    # UC12 - ADD AND REMOVE STUDENTS
    # =====================================================

    @classmethod
    def add_student(cls, section_id, student_id):
        section = db.session.get(ClassSection, section_id)
        student = db.session.get(Student, student_id)

        if not section or not student:
            cls._fail(
                NOT_FOUND,
                "Class section or student not found.",
                404
            )

        existing = Enrollment.query.filter_by(
            section_id=section_id,
            student_id=student_id
        ).first()

        if existing:
            cls._fail(
                DUPLICATE_VALUE,
                "Student is already enrolled.",
                409
            )

        enrollment = Enrollment(
            section_id=section_id,
            student_id=student_id
        )

        db.session.add(enrollment)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            cls._fail(
                DUPLICATE_VALUE,
                "Student is already enrolled.",
                409
            )

        return enrollment

    @classmethod
    def add_student_by_code(cls, section_id, student_code):
        student_code = (student_code or "").strip()

        if not student_code or len(student_code) > 20:
            cls._fail(
                VALIDATION_ERROR,
                "Invalid student code."
            )

        student = Student.query.filter(
            func.lower(Student.student_code)
            == student_code.lower()
        ).first()

        if not student:
            cls._fail(
                NOT_FOUND,
                "Student code does not exist.",
                404
            )

        return cls.add_student(
            section_id,
            student.user_id
        )

    @classmethod
    def _student_has_attendance(cls, section_id, student_id):
        return (
            db.session.query(Attendance.id)
            .join(
                ClassSession,
                Attendance.session_id == ClassSession.id
            )
            .filter(
                ClassSession.section_id == section_id,
                Attendance.student_id == student_id
            )
            .first()
            is not None
        )

    @classmethod
    def remove_student(cls, section_id, student_id):
        enrollment = Enrollment.query.filter_by(
            section_id=section_id,
            student_id=student_id
        ).first()

        if not enrollment:
            cls._fail(
                NOT_FOUND,
                "Student enrollment not found.",
                404
            )

        if cls._student_has_attendance(
            section_id,
            student_id
        ):
            cls._fail(
                STUDENT_HAS_ATTENDANCE,
                "Cannot remove a student with attendance records.",
                409
            )

        db.session.delete(enrollment)
        db.session.commit()

    # =====================================================
    # UC12 - IMPORT STUDENTS FROM EXCEL
    # =====================================================

    @classmethod
    def import_students_excel(cls, section_id, uploaded_file):

        if not db.session.get(ClassSection, section_id):
            cls._fail(
                NOT_FOUND,
                "Class section not found.",
                404
            )

        if (
            not uploaded_file
            or not uploaded_file.filename.lower().endswith(".xlsx")
        ):
            cls._fail(
                VALIDATION_ERROR,
                "Please upload an .xlsx Excel file."
            )

        try:
            from openpyxl import load_workbook

            workbook = load_workbook(
                uploaded_file,
                read_only=True,
                data_only=True
            )

            sheet = workbook.active

        except Exception:
            cls._fail(
                VALIDATION_ERROR,
                "Unable to read Excel file."
            )

        imported = []
        skipped = []
        errors = []
        seen = set()

        try:
            rows = sheet.iter_rows(
                min_col=1,
                max_col=1,
                values_only=True
            )

            for row_number, row in enumerate(rows, start=1):

                raw = row[0]
                code = str(raw).strip() if raw is not None else ""

                if not code:
                    continue

                if row_number == 1 and code.lower() in {
                    "student_code",
                    "student code",
                    "student_id",
                    "mã sinh viên",
                    "ma sinh vien"
                }:
                    continue

                normalized = code.casefold()

                if normalized in seen:
                    skipped.append({
                        "row": row_number,
                        "student_code": code,
                        "reason": "Duplicate row in Excel file"
                    })
                    continue

                seen.add(normalized)

                student = Student.query.filter(
                    func.lower(Student.student_code)
                    == code.lower()
                ).first()

                if not student:
                    errors.append({
                        "row": row_number,
                        "student_code": code,
                        "message": f"Student code '{code}' does not exist."
                    })
                    continue

                existing = Enrollment.query.filter_by(
                    section_id=section_id,
                    student_id=student.user_id
                ).first()

                if existing:
                    skipped.append({
                        "row": row_number,
                        "student_code": code,
                        "reason": "Student is already enrolled"
                    })
                    continue

                db.session.add(
                    Enrollment(
                        section_id=section_id,
                        student_id=student.user_id
                    )
                )

                imported.append({
                    "row": row_number,
                    "student_code": code
                })

            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            cls._fail(
                DUPLICATE_VALUE,
                "Excel import conflict. Please try again.",
                409
            )

        finally:
            workbook.close()

        return {
            "success_count": len(imported),
            "skipped_count": len(skipped),
            "error_count": len(errors),
            "ok_rows": imported,
            "skipped_rows": skipped,
            "error_rows": errors
        }

    # =====================================================
    # UC16 - VIEW TEACHING CLASSES
    # =====================================================

    @classmethod
    def teaching_classes(cls, lecturer_id, semester=None):

        query = ClassSection.query.filter_by(
            lecturer_id=lecturer_id
        )

        if semester:
            query = query.filter_by(semester=semester)

        sections = (
            query.join(Course)
            .order_by(
                ClassSection.semester.desc(),
                Course.code,
                ClassSection.id
            )
            .all()
        )

        today = date.today()
        result = []

        for section in sections:

            sessions = list(section.sessions)

            held = sum(
                1 for item in sessions
                if item.session_date <= today
            )

            result.append({
                "section": section,
                "section_id": section.id,
                "course_code": section.course.code,
                "course_name": section.course.name,
                "room": section.room,
                "student_count": len(section.enrollments),
                "held": held,
                "total_sessions": len(sessions)
            })

        return result

    @classmethod
    def teaching_class_detail(
        cls,
        lecturer_id,
        section_id,
        student_page=1,
        per_page=20
    ):

        section = db.session.get(ClassSection, section_id)

        if not section:
            cls._fail(
                NOT_FOUND,
                "Class section not found.",
                404
            )

        if section.lecturer_id != lecturer_id:
            cls._fail(
                "NOT_OWNER_SECTION",
                "You are not assigned to this class.",
                403
            )

        pagination = (
            Student.query
            .join(
                Enrollment,
                Enrollment.student_id == Student.user_id
            )
            .filter(Enrollment.section_id == section_id)
            .order_by(Student.student_code)
            .paginate(
                page=max(1, student_page),
                per_page=min(100, max(1, per_page)),
                error_out=False
            )
        )

        student_rows = []

        for student in pagination.items:
            student_rows.append({
                "student": student,
                "student_id": student.user_id,
                "student_code": student.student_code,
                "full_name": student.full_name
            })

        sessions = []

        for item in section.sessions:

            attendance_count = Attendance.query.filter_by(
                session_id=item.id
            ).count()

            sessions.append({
                "session": item,
                "session_id": item.id,
                "session_date": item.session_date,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "attendance_taken": attendance_count > 0,
                "attendance_count": attendance_count
            })

        return (
            section,
            pagination,
            student_rows,
            sessions
        )

    # =====================================================
    # ACTION DISPATCHER
    # =====================================================

    @staticmethod
    def manage_sections(action, **data):

        actions = {
            "create_course": lambda: ClassService.create_course(
                data.get("code"),
                data.get("name"),
                data.get("credits")
            ),

            "update_course": lambda: ClassService.update_course(
                data.get("course_id"),
                data.get("code"),
                data.get("name"),
                data.get("credits")
            ),

            "delete_course": lambda: ClassService.delete_course(
                data.get("course_id")
            ),

            "create_section": lambda: ClassService.create_section(
                data.get("course_id"),
                data.get("semester"),
                data.get("room"),
                data.get("lecturer_id")
            ),

            "update_section": lambda: ClassService.update_section(
                data.get("section_id"),
                data.get("course_id"),
                data.get("semester"),
                data.get("room"),
                data.get("lecturer_id")
            ),

            "add_student": lambda: ClassService.add_student(
                data.get("section_id"),
                data.get("student_id")
            ),

            "add_student_by_code": lambda: ClassService.add_student_by_code(
                data.get("section_id"),
                data.get("student_code")
            ),

            "remove_student": lambda: ClassService.remove_student(
                data.get("section_id"),
                data.get("student_id")
            )
        }

        if action not in actions:
            ClassService._fail(
                VALIDATION_ERROR,
                "Invalid class management action."
            )

        return actions[action]()


class SessionService:
    """UC13 - Manage Sessions."""

    @staticmethod
    def _fail(code, message, status=400):
        raise ServiceError(code, message, status)

    @staticmethod
    def _parse_date(value, field_name="session_date"):
        try:
            return date.fromisoformat(str(value))
        except (TypeError, ValueError):
            SessionService._fail(
                VALIDATION_ERROR,
                f"{field_name} must use YYYY-MM-DD format."
            )

    @staticmethod
    def _parse_time(value, field_name):
        try:
            return time.fromisoformat(str(value))
        except (TypeError, ValueError):
            SessionService._fail(
                VALIDATION_ERROR,
                f"{field_name} must use HH:MM format."
            )

    @classmethod
    def _validate_time_and_overlap(
        cls,
        section_id,
        session_date,
        start_time,
        end_time,
        exclude_session_id=None
    ):

        if end_time <= start_time:
            cls._fail(
                VALIDATION_ERROR,
                "End time must be after start time."
            )

        query = ClassSession.query.filter(
            ClassSession.section_id == section_id,
            ClassSession.session_date == session_date,
            ClassSession.start_time < end_time,
            ClassSession.end_time > start_time
        )

        if exclude_session_id is not None:
            query = query.filter(
                ClassSession.id != exclude_session_id
            )

        if query.first():
            cls._fail(
                VALIDATION_ERROR,
                "Session overlaps another session in this class.",
                409
            )

    @classmethod
    def create_session(
        cls,
        section_id,
        session_date,
        start_time,
        end_time
    ):

        if not db.session.get(ClassSection, section_id):
            cls._fail(
                NOT_FOUND,
                "Class section not found.",
                404
            )

        day = cls._parse_date(session_date)
        start = cls._parse_time(start_time, "start_time")
        end = cls._parse_time(end_time, "end_time")

        cls._validate_time_and_overlap(
            section_id,
            day,
            start,
            end
        )

        item = ClassSession(
            section_id=section_id,
            session_date=day,
            start_time=start,
            end_time=end
        )

        db.session.add(item)
        db.session.commit()

        return item

    @classmethod
    def create_weekly_sessions(
        cls,
        section_id,
        start_date,
        weekday,
        start_time,
        end_time,
        count
    ):

        if not db.session.get(ClassSection, section_id):
            cls._fail(
                NOT_FOUND,
                "Class section not found.",
                404
            )

        first_day = cls._parse_date(
            start_date,
            "start_date"
        )

        try:
            weekday = int(weekday)
            count = int(count)
        except (TypeError, ValueError):
            cls._fail(
                VALIDATION_ERROR,
                "Weekday and count must be integers."
            )

        if weekday not in range(7):
            cls._fail(
                VALIDATION_ERROR,
                "Weekday must be between 0 and 6."
            )

        if count < 1 or count > 52:
            cls._fail(
                VALIDATION_ERROR,
                "Number of weeks must be between 1 and 52."
            )

        start = cls._parse_time(start_time, "start_time")
        end = cls._parse_time(end_time, "end_time")

        first_day += timedelta(
            days=(weekday - first_day.weekday()) % 7
        )

        created = []

        for offset in range(count):

            day = first_day + timedelta(days=offset * 7)

            cls._validate_time_and_overlap(
                section_id,
                day,
                start,
                end
            )

            created.append(
                ClassSession(
                    section_id=section_id,
                    session_date=day,
                    start_time=start,
                    end_time=end
                )
            )

        db.session.add_all(created)
        db.session.commit()

        return created

    @classmethod
    def update_session(
        cls,
        session_id,
        session_date,
        start_time,
        end_time
    ):

        item = db.session.get(ClassSession, session_id)

        if not item:
            cls._fail(
                NOT_FOUND,
                "Session not found.",
                404
            )

        if Attendance.query.filter_by(
            session_id=session_id
        ).first():
            cls._fail(
                SESSION_HAS_ATTENDANCE,
                "Cannot edit a session with attendance records.",
                409
            )

        day = cls._parse_date(session_date)
        start = cls._parse_time(start_time, "start_time")
        end = cls._parse_time(end_time, "end_time")

        cls._validate_time_and_overlap(
            item.section_id,
            day,
            start,
            end,
            item.id
        )

        item.session_date = day
        item.start_time = start
        item.end_time = end

        db.session.commit()

        return item

    @classmethod
    def delete_session(cls, session_id):

        item = db.session.get(ClassSession, session_id)

        if not item:
            cls._fail(
                NOT_FOUND,
                "Session not found.",
                404
            )

        if Attendance.query.filter_by(
            session_id=session_id
        ).first():
            cls._fail(
                SESSION_HAS_ATTENDANCE,
                "Cannot delete a session with attendance records.",
                409
            )

        db.session.delete(item)
        db.session.commit()

    @staticmethod
    def manage_sessions(action, **data):

        actions = {
            "create": lambda: SessionService.create_session(
                data.get("section_id"),
                data.get("session_date"),
                data.get("start_time"),
                data.get("end_time")
            ),

            "create_weekly": lambda: SessionService.create_weekly_sessions(
                data.get("section_id"),
                data.get("start_date"),
                data.get("weekday"),
                data.get("start_time"),
                data.get("end_time"),
                data.get("count")
            ),

            "update": lambda: SessionService.update_session(
                data.get("session_id"),
                data.get("session_date"),
                data.get("start_time"),
                data.get("end_time")
            ),

            "delete": lambda: SessionService.delete_session(
                data.get("session_id")
            )
        }

        if action not in actions:
            SessionService._fail(
                VALIDATION_ERROR,
                "Invalid session management action."
            )

        return actions[action]()
