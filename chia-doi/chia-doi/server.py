#!/usr/bin/env python3
"""API cho app Chia đội bóng.

- Mọi người đều tự quay thử được ngay trên trình duyệt của mình (không lưu gì).
- Admin đăng nhập bằng mật khẩu, kết quả admin quay được lưu vào data.json
  và công bố cho mọi người xem. Admin quay lại thì ghi đè kết quả cũ.
- Chỉ dùng thư viện chuẩn của Python 3, không cần cài thêm gì.

Chạy:  ADMIN_PASSWORD='mat-khau-cua-ban' python3 server.py
"""
import json
import os
import secrets
import sys
import threading
import time
from datetime import datetime, timezone
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if len(PASSWORD) < 6:
    sys.exit("Thiếu biến ADMIN_PASSWORD (tối thiểu 6 ký tự).")

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "3000"))
DATA = os.environ.get(
    "DATA_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
)
SESSION_TTL = 12 * 3600
MAX_PLAYERS = 40
MAX_FAILS = 5
LOCK_SECONDS = 60

lock = threading.Lock()
sessions = {}  # token -> thời điểm hết hạn
fails = {}  # ip -> [số lần sai, khoá đến lúc]
rng = secrets.SystemRandom()


def load_state():
    try:
        with open(DATA, encoding="utf-8") as f:
            data = json.load(f)
            return {
                "result": data.get("result"),
                "scorers": data.get("scorers") or [],
                "assists": data.get("assists") or [],
            }
    except (OSError, ValueError, AttributeError):
        return {"result": None, "scorers": [], "assists": []}


def save_state():
    tmp = DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(tmp, DATA)


state = load_state()
STATS_FIELD = {"scorers": "goals", "assists": "assists"}
MAX_STATS = 200


class Handler(BaseHTTPRequestHandler):
    server_version = "ChiaDoi/1.0"

    # ----- tiện ích -----
    def client_ip(self):
        return self.headers.get("X-Real-IP") or self.client_address[0]

    def send_json(self, code, obj, cookie=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def session_token(self):
        try:
            morsel = SimpleCookie(self.headers.get("Cookie", "")).get("adm")
        except CookieError:
            return None
        return morsel.value if morsel else None

    def is_admin(self):
        token = self.session_token()
        if not token:
            return False
        with lock:
            expires = sessions.get(token)
            if expires and expires > time.time():
                return True
            sessions.pop(token, None)
        return False

    def read_json(self):
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return None
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > 65536:
            return None
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    # ----- GET -----
    def do_GET(self):
        if self.path.split("?")[0] == "/api/state":
            with lock:
                result = state["result"]
                scorers = state["scorers"]
                assists = state["assists"]
            self.send_json(200, {
                "result": result,
                "scorers": scorers,
                "assists": assists,
                "admin": self.is_admin(),
            })
        else:
            self.send_json(404, {"error": "Không tìm thấy."})

    # ----- POST -----
    def do_POST(self):
        route = self.path.split("?")[0]
        if route == "/api/login":
            return self.login()
        if route == "/api/logout":
            return self.logout()
        if route == "/api/spin":
            return self.spin()
        if route == "/api/reset":
            return self.reset()
        if route == "/api/scorers":
            return self.set_stats("scorers")
        if route == "/api/assists":
            return self.set_stats("assists")
        self.send_json(404, {"error": "Không tìm thấy."})

    def login(self):
        data = self.read_json()
        if data is None:
            return self.send_json(400, {"error": "Dữ liệu không hợp lệ."})
        ip = self.client_ip()
        now = time.time()
        with lock:
            record = fails.get(ip, [0, 0])
            if record[1] > now:
                return self.send_json(429, {"error": "Sai nhiều lần, thử lại sau ít phút."})
        given = str(data.get("password", "")).encode("utf-8")
        if secrets.compare_digest(given, PASSWORD.encode("utf-8")):
            token = secrets.token_urlsafe(32)
            with lock:
                fails.pop(ip, None)
                sessions[token] = now + SESSION_TTL
            cookie = "adm=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=%d" % (token, SESSION_TTL)
            return self.send_json(200, {"ok": True}, cookie)
        time.sleep(0.5)
        with lock:
            record = fails.get(ip, [0, 0])
            record[0] += 1
            if record[0] >= MAX_FAILS:
                record = [0, now + LOCK_SECONDS]
            fails[ip] = record
        self.send_json(401, {"error": "Sai mật khẩu."})

    def logout(self):
        token = self.session_token()
        if token:
            with lock:
                sessions.pop(token, None)
        self.send_json(200, {"ok": True}, "adm=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")

    def spin(self):
        if not self.is_admin():
            return self.send_json(401, {"error": "Cần đăng nhập admin."})
        data = self.read_json()
        raw = data.get("players") if data else None
        if not isinstance(raw, list):
            return self.send_json(400, {"error": "Danh sách không hợp lệ."})
        names, seen = [], set()
        for item in raw:
            if not isinstance(item, str):
                continue
            name = " ".join(item.split())[:30]
            key = name.casefold()
            if name and key not in seen:
                seen.add(key)
                names.append(name)
        if not 2 <= len(names) <= MAX_PLAYERS:
            return self.send_json(400, {"error": "Cần từ 2 đến %d người." % MAX_PLAYERS})
        with lock:
            # Admin quay lại thì kết quả mới ghi đè kết quả đã công bố trước đó.
            order = names[:]
            rng.shuffle(order)
            first = rng.randrange(2)
            result = {
                "blue": [n for i, n in enumerate(order) if (i + first) % 2 == 0],
                "red": [n for i, n in enumerate(order) if (i + first) % 2 == 1],
                "order": order,
                "first": first,
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            }
            state["result"] = result
            try:
                save_state()
            except OSError:
                return self.send_json(500, {"error": "Không ghi được dữ liệu trên máy chủ."})
        self.send_json(200, {"result": result})

    def reset(self):
        if not self.is_admin():
            return self.send_json(401, {"error": "Cần đăng nhập admin."})
        with lock:
            state["result"] = None
            try:
                save_state()
            except OSError:
                return self.send_json(500, {"error": "Không ghi được dữ liệu trên máy chủ."})
        self.send_json(200, {"ok": True})

    def set_stats(self, kind):
        if not self.is_admin():
            return self.send_json(401, {"error": "Cần đăng nhập admin."})
        data = self.read_json()
        raw = data.get("items") if data else None
        if not isinstance(raw, list):
            return self.send_json(400, {"error": "Dữ liệu không hợp lệ."})
        field = STATS_FIELD[kind]
        items, seen = [], set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = " ".join(str(item.get("name", "")).split())[:30]
            if not name:
                continue
            key = name.casefold()
            if key in seen:
                continue
            try:
                value = int(item.get(field, 0))
            except (TypeError, ValueError):
                continue
            value = max(0, min(999, value))
            seen.add(key)
            items.append({"name": name, field: value})
            if len(items) >= MAX_STATS:
                break
        with lock:
            state[kind] = items
            try:
                save_state()
            except OSError:
                return self.send_json(500, {"error": "Không ghi được dữ liệu trên máy chủ."})
        self.send_json(200, {"items": items})


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print("Chia doi API chay tai http://%s:%d" % (HOST, PORT), flush=True)
    server.serve_forever()
