FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=wsgi

WORKDIR /app

# Thư viện của dự án + 2 gói chỉ cần khi chạy bằng Docker:
#   gunicorn     máy chủ chạy thật (thay cho `flask run`)
#   cryptography PyMySQL cần để đăng nhập MySQL 8 (caching_sha2_password)
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && pip install "gunicorn==23.0.0" "cryptography==44.0.3"

COPY . .

# Sửa xuống dòng kiểu Windows (CRLF) nếu có, để script chạy được trong Linux
RUN sed -i 's/\r$//' docker/entrypoint.sh \
    && chmod +x docker/entrypoint.sh \
    && useradd --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# entrypoint: chạy migration (và seed nếu SEED_ON_START=1) rồi mới chạy lệnh bên dưới
ENTRYPOINT ["./docker/entrypoint.sh"]

# 1 worker + nhiều luồng: bộ đếm khóa nhập sai mã (NFR11) nằm trong bộ nhớ tiến trình,
# nhiều worker sẽ mỗi worker đếm riêng.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--access-logfile", "-", "wsgi:app"]
