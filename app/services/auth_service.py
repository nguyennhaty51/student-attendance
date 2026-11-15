from flask_login import login_user, logout_user
from app.extensions import db
from app.models.user import User


class AuthService:
    @staticmethod
    def login(username: str, password: str):
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return None, "Tên đăng nhập hoặc mật khẩu không chính xác."
        if not user.is_active:
            return None, "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên."
        login_user(user)
        return user, None

    @staticmethod
    def logout() -> None:
        logout_user()

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str):
        if not user.check_password(old_password):
            return False, "Mật khẩu cũ không chính xác."
        if not new_password or len(new_password) < 6:
            return False, "Mật khẩu mới phải có ít nhất 6 ký tự."
        user.set_password(new_password)
        db.session.commit()
        return True, "Đổi mật khẩu thành công."