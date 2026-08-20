# docker-optimize-lab

Lab thực hành: dùng **Claude Code** (kết nối qua GitHub MCP) để review và tối ưu một repo
FastAPI có Dockerfile chưa tối ưu + CI cơ bản.

## Cấu trúc

```
docker-optimize-lab/
├── app/
│   ├── main.py                # FastAPI app mẫu (3 endpoint: /, /health, /items)
│   ├── requirements.txt       # dependency runtime
│   └── requirements-dev.txt   # dependency dev/test (không nên có trong runtime image)
├── tests/
│   └── test_main.py
├── Dockerfile                 # CỐ Ý chưa tối ưu — xem comment trong file
├── .github/workflows/ci.yml   # CI cơ bản — build/test, chưa cache, chưa scan, chưa push
├── .claude/skills/repo-reviewer/SKILL.md   # skill để Claude Code review repo
└── README.md
```

## Lỗi cố ý trong Dockerfile (để bạn/Claude Code tìm ra)

1. `FROM python:latest` — không pin version, không dùng slim image.
2. `COPY . .` trước khi cài dependency → phá cache layer mỗi lần đổi code.
3. Cài `requirements-dev.txt` (pytest, httpx...) vào image production.
4. `apt-get install` nhiều package không cần thiết (vim, git, curl) và không dọn `apt` cache.
5. Không có multi-stage build.
6. Không có non-root `USER`.
7. Không có `HEALTHCHECK`.
8. CMD chạy `uvicorn --reload` (chế độ dev) trong image tưởng là production.
9. Không có `.dockerignore`.

CI cũng thiếu: layer caching, security scan (Trivy/Grype), push lên registry, `permissions:`
giới hạn quyền.

---

## Bước 1 — Đẩy repo này lên GitHub (bạn tự làm, dùng tài khoản/token của bạn)

```bash
cd docker-optimize-lab
git init
git add .
git commit -m "init: unoptimized docker-optimize-lab for Claude Code exercise"

# Cách A: dùng GitHub CLI (khuyên dùng nếu đã cài `gh` và đã `gh auth login`)
gh repo create docker-optimize-lab --private --source=. --remote=origin --push

# Cách B: tạo repo thủ công trên github.com rồi:
git remote add origin https://github.com/<username>/docker-optimize-lab.git
git branch -M main
git push -u origin main
```

## Bước 2 — Cài Claude Code (nếu chưa có)

```bash
npm install -g @anthropic-ai/claude-code
```

Sau đó vào thư mục repo và chạy:

```bash
cd docker-optimize-lab
claude
```

Claude Code sẽ tự nhận diện file trong `.claude/skills/repo-reviewer/SKILL.md` vì nó nằm đúng
chuẩn thư mục skill của Claude Code trong repo.

## Bước 3 — Kết nối GitHub qua MCP (để Claude Code có thể đọc issue/PR, tạo PR trực tiếp)

Trong phiên `claude`, chạy:

```
/mcp add github
```

hoặc thêm thủ công vào `~/.claude/settings.json` (hoặc `.mcp.json` trong repo nếu muốn scope theo
project):

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<token của bạn, scope repo>"
      }
    }
  }
}
```

> Token cần scope tối thiểu: `repo` (để đọc/ghi code, tạo PR). Không commit token vào repo —
> để trong biến môi trường hoặc secret manager của bạn.

## Bước 4 — Chạy review

Trong phiên Claude Code, gõ:

```
Review toàn bộ repo này (Dockerfile, CI, code) và đề xuất cải tiến.
```

Claude Code sẽ tự kích hoạt skill `repo-reviewer` (nhờ phần `description` trong SKILL.md khớp với
yêu cầu) và trả về đề xuất theo 3 nhóm: Dockerfile / CI / Code.

Nếu muốn Claude Code áp dụng fix trực tiếp và mở PR:

```
Áp dụng các fix ưu tiên cao nhất, tạo branch mới và mở PR qua GitHub MCP.
```

## Bước 5 (tuỳ chọn) — Kiểm chứng kết quả

```bash
# So sánh size image trước/sau khi tối ưu
docker build -t docker-optimize-lab:before .   # trước khi Claude Code sửa (checkout commit gốc)
docker build -t docker-optimize-lab:after .    # sau khi sửa
docker images | grep docker-optimize-lab
```

Image sau khi tối ưu (multi-stage + slim base + không cài dev deps) thường giảm được đáng kể so
với image gốc.
