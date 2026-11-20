from datetime import date, time, timedelta
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.errors import ServiceError
from app.models.user import User, Student, Lecturer
from app.models.enums import Role
from app.models.academic import Course, ClassSection, Enrollment, ClassSession
from app.models.attendance import Attendance

class AdminService:
    @staticmethod
    def _duplicate():
        raise ServiceError("DUPLICATE_VALUE", "Tên đăng nhập, email hoặc mã đã tồn tại.", 409)

    @staticmethod
    def create_user(data):
        role = data.get("role", "").upper()
        if role not in ("STUDENT", "LECTURER"):
            raise ServiceError("VALIDATION_ERROR", "Chỉ được tạo tài khoản sinh viên hoặc giảng viên.")
        required = ("username", "full_name", "email", "code")
        if any(not (data.get(k) or "").strip() for k in required):
            raise ServiceError("VALIDATION_ERROR", "Vui lòng nhập đầy đủ thông tin bắt buộc.")
        if User.query.filter((User.username == data["username"].strip()) |
                             (User.email == data["email"].strip())).first():
            AdminService._duplicate()
        try:
            temporary = "Init@" + __import__("secrets").token_urlsafe(7)
            common = dict(username=data["username"].strip(), full_name=data["full_name"].strip(),
                          email=data["email"].strip(), password=temporary, is_active=True)
            if role == "STUDENT":
                if Student.query.filter_by(student_code=data["code"].strip()).first():
                    AdminService._duplicate()
                obj = Student(**common, role=Role.STUDENT, student_code=data["code"].strip(),
                              class_name=(data.get("class_name") or "").strip() or None)
            else:
                if Lecturer.query.filter_by(lecturer_code=data["code"].strip()).first():
                    AdminService._duplicate()
                obj = Lecturer(**common, role=Role.LECTURER, lecturer_code=data["code"].strip(),
                               department=(data.get("department") or "").strip() or None)
            db.session.add(obj); db.session.commit()
            return obj, temporary
        except IntegrityError:
            db.session.rollback(); AdminService._duplicate()

    @staticmethod
    def update_user(user_id, data):
        user = db.session.get(User, int(user_id))
        if not user: raise ServiceError("NOT_FOUND", "Không tìm thấy người dùng.", 404)
        email = (data.get("email") or "").strip()
        duplicate = User.query.filter(User.email == email, User.id != user.id).first() if email else None
        if duplicate: AdminService._duplicate()
        if not (data.get("full_name") or "").strip() or not email:
            raise ServiceError("VALIDATION_ERROR", "Họ tên và email không được để trống.")
        user.full_name, user.email = data["full_name"].strip(), email
        if isinstance(user, Student): user.class_name = (data.get("class_name") or "").strip() or None
        if isinstance(user, Lecturer): user.department = (data.get("department") or "").strip() or None
        db.session.commit()

    @staticmethod
    def set_active(user_id, active):
        user = db.session.get(User, int(user_id))
        if not user: raise ServiceError("NOT_FOUND", "Không tìm thấy người dùng.", 404)
        if user.role == Role.ADMIN: raise ServiceError("VALIDATION_ERROR", "Không thể khóa tài khoản quản trị.")
        user.is_active = bool(active); db.session.commit()

    @staticmethod
    def reset_password(user_id):
        user = db.session.get(User, int(user_id))
        if not user: raise ServiceError("NOT_FOUND", "Không tìm thấy người dùng.", 404)
        temporary = "Reset@" + __import__("secrets").token_urlsafe(6)
        user.set_password(temporary); db.session.commit()
        return temporary

    @staticmethod
    def add_section(course_id, semester, room, lecturer_id):
        course = db.session.get(Course, int(course_id))
        lecturer = db.session.get(Lecturer, int(lecturer_id))
        if not course or not lecturer or not semester.strip():
            raise ServiceError("VALIDATION_ERROR", "Môn học, giảng viên và học kỳ là bắt buộc.")
        section = ClassSection(course_id=course.id, semester=semester.strip(),
                               room=(room or "").strip() or None, lecturer_id=lecturer.id)
        db.session.add(section); db.session.commit(); return section

    @staticmethod
    def add_student(section_id, student_code):
        section = db.session.get(ClassSection, int(section_id))
        student = Student.query.filter_by(student_code=student_code.strip()).first()
        if not section or not student: raise ServiceError("NOT_FOUND", "Không tìm thấy lớp hoặc sinh viên.", 404)
        if Enrollment.query.filter_by(section_id=section.id, student_id=student.user_id).first():
            raise ServiceError("DUPLICATE_VALUE", "Sinh viên đã có trong lớp.", 409)
        db.session.add(Enrollment(section_id=section.id, student_id=student.user_id)); db.session.commit()

    @staticmethod
    def remove_student(section_id, student_id):
        enrollment = Enrollment.query.filter_by(section_id=int(section_id), student_id=int(student_id)).first()
        if not enrollment: raise ServiceError("NOT_FOUND", "Không tìm thấy sinh viên trong lớp.", 404)
        has_attendance = Attendance.query.join(ClassSession).filter(
            ClassSession.section_id == int(section_id), Attendance.student_id == int(student_id)).first()
        if has_attendance: raise ServiceError("STUDENT_HAS_ATTENDANCE", "Sinh viên đã có dữ liệu điểm danh.", 409)
        db.session.delete(enrollment); db.session.commit()

    @staticmethod
    def import_students(section_id, file_storage):
        from openpyxl import load_workbook
        try:
            wb = load_workbook(file_storage, read_only=True, data_only=True)
            ws = wb.active
        except Exception:
            raise ServiceError("VALIDATION_ERROR", "Không đọc được file Excel .xlsx.")
        ok, errors = 0, []
        for row_num, cells in enumerate(ws.iter_rows(min_col=1, max_col=1, values_only=True), start=1):
            code = str(cells[0] or "").strip()
            if not code:
                continue
            if row_num == 1 and code.lower() in ("mã sinh viên", "student_code", "student code"):
                continue
            try:
                AdminService.add_student(section_id, code); ok += 1
            except ServiceError as exc:
                errors.append({"row": row_num, "message": exc.message})
        wb.close()
        return {"ok_rows": ok, "error_rows": errors}

    @staticmethod
    def create_session(section_id, session_date, start_time, end_time):
        section = db.session.get(ClassSection, int(section_id))
        if not section: raise ServiceError("NOT_FOUND", "Không tìm thấy lớp học phần.", 404)
        d, st, et = date.fromisoformat(session_date), time.fromisoformat(start_time), time.fromisoformat(end_time)
        if et <= st: raise ServiceError("VALIDATION_ERROR", "Giờ kết thúc phải sau giờ bắt đầu.")
        session = ClassSession(section_id=section.id, session_date=d, start_time=st, end_time=et)
        db.session.add(session); db.session.commit(); return session

    @staticmethod
    def create_weekly(section_id, start_date, weekday, start_time, end_time, count):
        try:
            first = date.fromisoformat(start_date); weekday=int(weekday); count=int(count)
            if weekday not in range(7) or not 1 <= count <= 30: raise ValueError()
            st, et = time.fromisoformat(start_time), time.fromisoformat(end_time)
            if et <= st: raise ValueError()
        except (ValueError, TypeError):
            raise ServiceError("VALIDATION_ERROR", "Thông tin lịch hàng tuần không hợp lệ (số buổi 1–30).")
        offset = (weekday - first.weekday()) % 7
        dates = [first + timedelta(days=offset + 7*i) for i in range(count)]
        section = db.session.get(ClassSection, int(section_id))
        if not section: raise ServiceError("NOT_FOUND", "Không tìm thấy lớp học phần.", 404)
        try:
            for d in dates:
                db.session.add(ClassSession(section_id=section.id, session_date=d, start_time=st, end_time=et))
            db.session.commit()
        except Exception:
            db.session.rollback(); raise

    @staticmethod
    def update_session(session_id, session_date, start_time, end_time):
        session = db.session.get(ClassSession, int(session_id))
        if not session: raise ServiceError("NOT_FOUND", "Không tìm thấy buổi học.", 404)
        if session.attendances: raise ServiceError("SESSION_HAS_ATTENDANCE", "Buổi học đã có điểm danh, không thể sửa.", 409)
        d, st, et = date.fromisoformat(session_date), time.fromisoformat(start_time), time.fromisoformat(end_time)
        if et <= st: raise ServiceError("VALIDATION_ERROR", "Giờ kết thúc phải sau giờ bắt đầu.")
        session.session_date, session.start_time, session.end_time = d, st, et
        db.session.commit()

    @staticmethod
    def delete_session(session_id):
        session = db.session.get(ClassSession, int(session_id))
        if not session: raise ServiceError("NOT_FOUND", "Không tìm thấy buổi học.", 404)
        if session.attendances: raise ServiceError("SESSION_HAS_ATTENDANCE", "Buổi học đã có điểm danh, không thể xóa.", 409)
        db.session.delete(session); db.session.commit()
