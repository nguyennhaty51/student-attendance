from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required
from sqlalchemy import or_
from app.models.user import User, Student, Lecturer
from app.models.academic import Course, ClassSection, ClassSession, Enrollment
from app.models.attendance import Attendance
from app.models.enums import Role
from app.services.admin_service import AdminService
from app.errors import ServiceError
from app.utils.decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def _run(action, success):
    try:
        action()
        flash(success, "success")
    except (ServiceError, ValueError) as exc:
        flash(getattr(exc, "message", str(exc)), "danger")

@admin_bp.get("/users")
@login_required
@role_required(Role.ADMIN)
def users():
    q=request.args.get("q","").strip(); role=request.args.get("role","").upper()
    query=User.query
    if q:
        like=f"%{q}%"
        query=query.filter(or_(User.username.ilike(like), User.full_name.ilike(like), User.email.ilike(like)))
    if role in ("STUDENT","LECTURER","ADMIN"): query=query.filter(User.role==Role[role])
    page=max(1,request.args.get("page",1,type=int)); pagination=query.order_by(User.id.desc()).paginate(page=page,per_page=20,error_out=False)
    rows=[]
    for u in pagination.items:
        code=u.student_code if isinstance(u,Student) else (u.lecturer_code if isinstance(u,Lecturer) else "—")
        rows.append(dict(user=u,code=code))
    return render_template("admin/users.html", users=rows, page=page, pages=pagination.pages, q=q, role_filter=role)

@admin_bp.post("/users")
@login_required
@role_required(Role.ADMIN)
def user_create():
    try:
        _user, temporary = AdminService.create_user(request.form)
        flash(f"Đã tạo tài khoản. Mật khẩu tạm (chỉ hiển thị lần này): {temporary}", "warning")
    except ServiceError as exc:
        flash(exc.message, "danger")
    return redirect(url_for("admin.users"))

@admin_bp.route("/users/<int:user_id>/edit",methods=["GET","POST"])
@login_required
@role_required(Role.ADMIN)
def user_edit(user_id):
    user=User.query.get_or_404(user_id)
    if request.method=="POST":
        _run(lambda: AdminService.update_user(user_id,request.form), "Đã cập nhật người dùng.")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_edit.html", user=user)

@admin_bp.post("/users/<int:user_id>/lock")
@login_required
@role_required(Role.ADMIN)
def user_lock(user_id):
    _run(lambda: AdminService.set_active(user_id,False),"Đã khóa tài khoản.")
    return redirect(url_for("admin.users"))

@admin_bp.post("/users/<int:user_id>/unlock")
@login_required
@role_required(Role.ADMIN)
def user_unlock(user_id):
    _run(lambda: AdminService.set_active(user_id,True),"Đã mở khóa tài khoản.")
    return redirect(url_for("admin.users"))

@admin_bp.post("/users/<int:user_id>/reset-password")
@login_required
@role_required(Role.ADMIN)
def user_reset(user_id):
    try:
        temp=AdminService.reset_password(user_id)
        flash(f"Mật khẩu tạm (chỉ hiển thị lần này): {temp}","warning")
    except ServiceError as exc: flash(exc.message,"danger")
    return redirect(url_for("admin.users"))

@admin_bp.get("/sections")
@login_required
@role_required(Role.ADMIN)
def sections():
    semester=request.args.get("semester","").strip()
    query=ClassSection.query
    if semester: query=query.filter_by(semester=semester)
    sections=query.order_by(ClassSection.id.desc()).all()
    selected_id=request.args.get("section_id",type=int)
    selected=next((s for s in sections if s.id==selected_id),None)
    students=[]
    if selected:
        for e in selected.enrollments:
            has=Attendance.query.join(ClassSession).filter(ClassSession.section_id==selected.id,Attendance.student_id==e.student_id).first() is not None
            students.append({"student":e.student,"has_attendance":has})
    semesters=[x[0] for x in ClassSection.query.with_entities(ClassSection.semester).distinct().all()]
    return render_template("admin/sections.html",sections=sections,courses=Course.query.order_by(Course.code).all(),
        lecturers=Lecturer.query.order_by(Lecturer.full_name).all(),students=students,selected=selected,
        semester=semester,semesters=semesters,import_result=None)

@admin_bp.post("/sections")
@login_required
@role_required(Role.ADMIN)
def section_create():
    _run(lambda: AdminService.add_section(request.form.get("course_id"),request.form.get("semester",""),
        request.form.get("room",""),request.form.get("lecturer_id")),"Đã tạo lớp học phần.")
    return redirect(url_for("admin.sections"))

@admin_bp.post("/sections/<int:section_id>/students")
@login_required
@role_required(Role.ADMIN)
def student_add(section_id):
    _run(lambda: AdminService.add_student(section_id,request.form.get("student_code","")),"Đã thêm sinh viên vào lớp.")
    return redirect(url_for("admin.sections",section_id=section_id))

@admin_bp.post("/sections/<int:section_id>/students/import")
@login_required
@role_required(Role.ADMIN)
def student_import(section_id):
    f=request.files.get("file")
    if not f or not f.filename.lower().endswith(".xlsx"):
        flash("Vui lòng chọn file .xlsx hợp lệ.","danger")
    else:
        try:
            result=AdminService.import_students(section_id,f)
            flash(f"Nhập thành công {result['ok_rows']} sinh viên; có {len(result['error_rows'])} dòng lỗi.","info")
            for error in result["error_rows"][:5]: flash(f"Dòng {error['row']}: {error['message']}","warning")
        except ServiceError as exc: flash(exc.message,"danger")
    return redirect(url_for("admin.sections",section_id=section_id))

@admin_bp.post("/sections/<int:section_id>/students/<int:student_id>/remove")
@login_required
@role_required(Role.ADMIN)
def student_remove(section_id,student_id):
    _run(lambda: AdminService.remove_student(section_id,student_id),"Đã gỡ sinh viên khỏi lớp.")
    return redirect(url_for("admin.sections",section_id=section_id))

@admin_bp.get("/sessions")
@login_required
@role_required(Role.ADMIN)
def sessions():
    sections=ClassSection.query.order_by(ClassSection.id.desc()).all()
    section_id=request.args.get("section_id",type=int)
    selected=next((s for s in sections if s.id==section_id),None)
    rows=[]
    if selected:
        for s in selected.sessions:
            rows.append({"session":s,"has_attendance":bool(s.attendances)})
    return render_template("admin/sessions.html",sections=sections,selected=selected,sessions=rows)

@admin_bp.post("/sessions")
@login_required
@role_required(Role.ADMIN)
def session_create():
    section_id=request.form.get("section_id")
    _run(lambda: AdminService.create_session(section_id,request.form.get("session_date",""),
        request.form.get("start_time",""),request.form.get("end_time","")),"Đã tạo buổi học.")
    return redirect(url_for("admin.sessions",section_id=section_id))

@admin_bp.post("/sessions/weekly")
@login_required
@role_required(Role.ADMIN)
def session_weekly():
    section_id=request.form.get("section_id")
    _run(lambda: AdminService.create_weekly(section_id,request.form.get("start_date",""),
        request.form.get("weekday"),request.form.get("start_time",""),request.form.get("end_time",""),
        request.form.get("count")),"Đã tạo lịch học hàng tuần.")
    return redirect(url_for("admin.sessions",section_id=section_id))

@admin_bp.post("/sessions/<int:session_id>/edit")
@login_required
@role_required(Role.ADMIN)
def session_edit(session_id):
    s=ClassSession.query.get_or_404(session_id)
    _run(lambda: AdminService.update_session(session_id,request.form.get("session_date",""),
        request.form.get("start_time",""),request.form.get("end_time","")),"Đã cập nhật buổi học.")
    return redirect(url_for("admin.sessions",section_id=s.section_id))

@admin_bp.post("/sessions/<int:session_id>/delete")
@login_required
@role_required(Role.ADMIN)
def session_delete(session_id):
    s=ClassSession.query.get_or_404(session_id); section_id=s.section_id
    _run(lambda: AdminService.delete_session(session_id),"Đã xóa buổi học.")
    return redirect(url_for("admin.sessions",section_id=section_id))
