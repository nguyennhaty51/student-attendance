"""Các đối tượng dùng chung (tránh import vòng)."""
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
