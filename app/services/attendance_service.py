from app.services.uc5_manual_attendance import ManualAttendanceMixin
from app.services.uc7_edit_attendance import EditAttendanceMixin


class AttendanceService(ManualAttendanceMixin, EditAttendanceMixin):
    pass