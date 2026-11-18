from __future__ import annotations

from sqlalchemy import func, select

from app.errors import FORBIDDEN, NOT_FOUND, ServiceError
from app.extensions import db
from app.models import Notification


class NotificationService:
    @staticmethod
    def list_for_user(user_id: int, unread_only: bool = False) -> list[Notification]:
        """Thông báo của người dùng, mới nhất trước (M07). `unread_only=True` chỉ lấy thông báo chưa đọc."""
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
        return list(db.session.scalars(stmt))

    @staticmethod
    def count_unread(user_id: int) -> int:
        """Số thông báo chưa đọc (hiện trên menu và trang chủ M03)."""
        return db.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, Notification.is_read.is_(False),
            )
        ) or 0

    @staticmethod
    def mark_as_read(user_id: int, notification_id: int) -> None:
        """Đánh dấu một thông báo đã đọc. Gọi lại với thông báo đã đọc thì không làm gì.

        Ném ServiceError: NOT_FOUND (không có thông báo), FORBIDDEN (thông báo của người khác).
        """
        notification = db.session.get(Notification, notification_id)
        if notification is None:
            raise ServiceError(NOT_FOUND, "Không tìm thấy thông báo.", 404)
        if notification.user_id != user_id:
            raise ServiceError(FORBIDDEN, "Bạn không có quyền với thông báo này.", 403)
        if not notification.is_read:
            notification.mark_as_read()
            db.session.commit()
