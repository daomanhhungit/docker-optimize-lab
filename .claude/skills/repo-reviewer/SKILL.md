---
name: repo-reviewer
description: Review toàn bộ repo (Dockerfile, GitHub Actions CI, và source code Python) rồi đề xuất cải tiến cụ thể, có thể áp dụng ngay. Kích hoạt skill này khi người dùng yêu cầu "review repo", "tối ưu Dockerfile", "kiểm tra CI", "audit dự án", hoặc bất kỳ yêu cầu nào liên quan đến việc rà soát chất lượng Dockerfile/CI/code trong repo hiện tại.
---

# Repo Reviewer

Skill này hướng dẫn Claude Code cách review một repo Python/FastAPI đóng gói bằng Docker, có
GitHub Actions CI, và đưa ra đề xuất cải tiến theo 3 nhóm: Dockerfile, CI pipeline, và code.

## Quy trình review

Khi được giao nhiệm vụ review, thực hiện theo thứ tự sau và luôn trình bày kết quả có cấu trúc
(không sửa file trừ khi người dùng yêu cầu rõ ràng "sửa giúp tôi" / "apply the fix"):

### 1. Đọc trước khi nhận xét
- Đọc toàn bộ `Dockerfile`, mọi file trong `.github/workflows/`, và các file Python liên quan
  (`app/`, `tests/`).
- Đọc `requirements.txt` / `requirements-dev.txt` để biết dependency nào thực sự cần ở runtime.
- Kiểm tra xem có `.dockerignore` hay không.

### 2. Review Dockerfile — kiểm tra các mục sau
- **Pin version base image**: `python:latest` hay tag không cố định? Đề xuất tag cụ thể
  (vd: `python:3.12-slim`).
- **Multi-stage build**: có tách build stage (cài build-essential, compile) khỏi runtime stage
  không? Nếu không, đề xuất tách để giảm size image.
- **Thứ tự COPY vs cài dependency**: `requirements.txt` có được COPY và install TRƯỚC khi COPY
  toàn bộ source không? Nếu source được copy trước, mọi lần sửa code đều làm mất cache của layer
  pip install — chỉ ra đây là vấn đề và đề xuất đảo thứ tự.
- **Dependency thừa ở runtime**: image production có cài `requirements-dev.txt` (pytest, httpx...)
  không? Nếu có, đề xuất tách dev deps ra khỏi runtime image.
- **Cleanup sau apt-get**: có `rm -rf /var/lib/apt/lists/*` sau `apt-get install` không? Có cài
  package không cần thiết (vd: vim, git, curl trong image chạy production) không?
- **Non-root user**: container có chạy bằng root không? Đề xuất tạo user riêng bằng `USER`.
- **HEALTHCHECK**: có định nghĩa HEALTHCHECK cho container không?
- **CMD phù hợp môi trường**: có đang chạy `--reload` (dev mode) trong image tưởng là production
  không? Đề xuất cấu hình uvicorn/gunicorn phù hợp (worker count, log level, không reload).
- **.dockerignore**: có tồn tại và loại trừ `.git`, `__pycache__`, `.venv`, `tests/`,
  file secrets... không?

### 3. Review CI (`.github/workflows/*.yml`)
- Có cache dependency (pip cache / `actions/setup-python` cache, hoặc Docker layer cache qua
  `buildx` + `cache-from`/`cache-to`) chưa?
- Có bước scan lỗ hổng image (vd: Trivy, Grype) chưa?
- Có build multi-arch (`linux/amd64`, `linux/arm64`) nếu cần chưa?
- Có push image lên registry (GHCR/Docker Hub) với tag rõ ràng (git sha, semver) chưa, hay chỉ
  build mà không push?
- Job `test` và `docker-build` có chạy song song một cách không cần thiết, hay phụ thuộc đúng thứ
  tự (`needs:`) chưa?
- Có giới hạn quyền (`permissions:`) theo nguyên tắc least privilege chưa?

### 4. Review code (mức nhẹ, không phải audit bảo mật toàn diện)
- Endpoint có xử lý lỗi input hợp lý không (vd: FastAPI + Pydantic validation đã đủ chưa)?
- Có endpoint `/health` phù hợp để dùng làm Docker HEALTHCHECK / k8s readiness probe không?
- Có test cho các nhánh lỗi (không chỉ happy path) không?

### 5. Trình bày kết quả
Luôn xuất kết quả theo 3 mục: **Dockerfile**, **CI**, **Code**. Với mỗi vấn đề tìm thấy:
- Trích dòng/đoạn liên quan.
- Giải thích ngắn gọn vì sao đó là vấn đề (tác động: build time, image size, bảo mật, độ tin cậy).
- Đề xuất fix cụ thể (đoạn code/config thay thế), không chỉ nói chung chung "nên tối ưu".

Ưu tiên đề xuất theo mức độ tác động: giảm attack surface & chạy non-root trước, sau đó đến giảm
image size / build time, cuối cùng là các cải tiến "nice to have".

## Khi được yêu cầu áp dụng fix
Nếu người dùng xác nhận muốn áp dụng, sửa trực tiếp file và tóm tắt diff bằng vài dòng — không cần
liệt kê lại toàn bộ nội dung file đã sửa.
