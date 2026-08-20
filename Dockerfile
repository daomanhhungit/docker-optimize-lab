# ==========================================================
# Dockerfile CHƯA TỐI ƯU - dùng để luyện tập review/optimize.
# Cố ý chứa nhiều "code smell" thường gặp trong production thật:
#   - base image không pin version, không phải slim
#   - cài build-essential nhưng không dọn dẹp
#   - copy toàn bộ source TRƯỚC khi cài dependency -> phá cache layer
#   - không dùng multi-stage build
#   - cài cả requirements-dev (không cần ở runtime)
#   - chạy bằng root, không có non-root user
#   - không có .dockerignore tương ứng (xem ghi chú README)
#   - không có HEALTHCHECK
#   - CMD chạy uvicorn dev mode, không set worker/log config
# ==========================================================
FROM python:latest

WORKDIR /app

# Copy toàn bộ source trước -> mọi thay đổi code đều làm mất cache của bước pip install
COPY . .

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    vim \
    && pip install --upgrade pip \
    && pip install -r app/requirements-dev.txt

EXPOSE 8000

# Chạy reload mode (dev) trong "production" image, chạy bằng root
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
