from app.services.uc5_manual_attendance import ManualAttendanceMixin
from app.services.uc7_edit_attendance import EditAttendanceMixin
from app.services.uc15_warning import WarningAttendanceMixin, get_threshold


class AttendanceService(
    ManualAttendanceMixin,
    EditAttendanceMixin,
    WarningAttendanceMixin,
):
    pass