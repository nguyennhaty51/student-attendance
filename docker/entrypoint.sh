#!/bin/sh
# Chạy mỗi lần container khởi động: migration -> (seed) -> chạy ứng dụng.
set -e

echo "[entrypoint] Chạy migration..."
tries=0
until flask --app wsgi db upgrade; do
  tries=$((tries + 1))
  if [ "$tries" -ge 15 ]; then
    echo "[entrypoint] Migration thất bại sau 15 lần thử. Xem lỗi phía trên." >&2
    exit 1
  fi
  echo "[entrypoint] CSDL chưa sẵn sàng, thử lại sau 3 giây ($tries/15)..."
  sleep 3
done

if [ "${SEED_ON_START:-0}" = "1" ]; then
  echo "[entrypoint] Nạp dữ liệu mẫu (chạy lại nhiều lần không bị trùng)..."
  python scripts/seed.py
fi

echo "[entrypoint] Khởi động ứng dụng..."
exec "$@"
