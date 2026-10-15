FROM python:3.12-slim

# Chạy bằng user thường, thư mục /data lưu kết quả quay
RUN useradd --system --uid 10001 app \
    && mkdir /app /data \
    && chown app /data

WORKDIR /app
COPY server.py .

ENV HOST=0.0.0.0 \
    PORT=3000 \
    DATA_FILE=/data/data.json \
    PYTHONUNBUFFERED=1

VOLUME /data
USER app
CMD ["python", "server.py"]
