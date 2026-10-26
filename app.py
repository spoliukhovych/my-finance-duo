"""Вебзастосунок: вхід за паролем перед Fava.

Хто що бачить:
  olya  → облік «Оля» і «Спільне»
  marko → облік «Марко» і «Спільне»
Без входу трекер не показує жодних даних. Чужий облік повертає 403.
Редактор файлів вимкнено: змінювати можна лише витрати, додані кнопкою «+».

Секрети беруться лише зі змінних середовища (у коді й у репозиторії їх немає):
  SECRET_KEY       — довгий випадковий рядок для підпису cookie
  OLYA_PASSWORD    — пароль Олі
  MARKO_PASSWORD   — пароль Марка
  ALLOW_HTTP=1     — лише для локальної перевірки на своєму компʼютері

Локально: SECRET_KEY=... OLYA_PASSWORD=... MARKO_PASSWORD=... ALLOW_HTTP=1 uv run app.py
На PythonAnywhere цей файл підключає WSGI-конфігурація (див. README).
"""
import hmac
import io
import json
import os
import sys
import time
from html import escape
from pathlib import Path
from urllib.parse import quote, urlparse

from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.wrappers import Request, Response

ROOT = Path(__file__).parent
LEDGERS = ROOT / "ledgers"
sys.path.insert(0, str(LEDGERS))  # щоб Fava знайшла розширення fava_report

from fava.application import create_app  # noqa: E402

COOKIE = "tracker_session"
SESSION_DAYS = 14
USERS = {
    "olya": {"name": "Оля", "env": "OLYA_PASSWORD", "ledgers": ["оля", "спільне"]},
    "marko": {"name": "Марко", "env": "MARKO_PASSWORD", "ledgers": ["марко", "спільне"]},
}
REPORT = "extension/FavaReport/"
MAX_FAILS, LOCK_SECONDS = 5, 60
UI = ROOT / "ui"  # спрощений вигляд Fava: simple.css, simple.js і report.css (звіти)
# Сторінки й дії Fava, які змінюють файли обліку. Редактор закрито, щоб випадково не зламати облік.
BLOCKED_PAGES = {"editor", "import"}
ALLOWED_WRITES = {"api/add_entries", "api/source_slice"}
# Спільний облік збирає importer.py з банківських виписок; вручну туди нічого не дописуємо.
READ_ONLY_LEDGERS = {"спільне"}


def _require_env(name):
    value = os.environ.get(name, "")
    if len(value) < 8:
        raise RuntimeError(f"Змінна середовища {name} не задана або коротша за 8 символів")
    return value


class Gate:
    """WSGI-обгортка: перевіряє вхід і доступ, а все інше передає у Fava."""

    def __init__(self):
        self.secret = _require_env("SECRET_KEY")
        self.passwords = {user: _require_env(info["env"]) for user, info in USERS.items()}
        self.allow_http = os.environ.get("ALLOW_HTTP") == "1"
        self.signer = URLSafeTimedSerializer(self.secret, salt="tracker-login")
        self.fails = {}  # ip → (кількість невдалих спроб, час останньої)
        files = [LEDGERS / f"{name}.beancount" for name in ("olya", "marko", "spilne")]
        self.fava = create_app(files, load=True, poll_watcher=True)

    # ---------- допоміжне ----------
    def user_from_cookie(self, request):
        token = request.cookies.get(COOKIE)
        if not token:
            return None
        try:
            user = self.signer.loads(token, max_age=SESSION_DAYS * 86400)
        except BadSignature:
            return None
        return user if user in USERS else None

    def is_https(self, environ):
        proto = environ.get("HTTP_X_FORWARDED_PROTO") or environ.get("wsgi.url_scheme", "http")
        return proto == "https"

    def locked(self, ip):
        count, last = self.fails.get(ip, (0, 0))
        return count >= MAX_FAILS and time.time() - last < LOCK_SECONDS

    # ---------- сторінки ----------
    def login_page(self, error="", next_url=""):
        html = f"""<!doctype html><html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Трекер для двох: вхід</title>
<style>
body {{ font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0; min-height: 100vh;
       display: flex; align-items: center; justify-content: center;
       background: linear-gradient(160deg, #ff5a5f, #ff8a5b); }}
form {{ background: #fff; padding: 28px 24px; border-radius: 24px; width: min(340px, 88vw); box-sizing: border-box;
       box-shadow: 0 12px 40px rgba(17,24,39,.18); color: #111827; }}
h1 {{ font-size: 22px; font-weight: 800; letter-spacing: -.02em; margin: 0 0 4px; }}
p {{ margin: 0 0 12px; color: #6b7280; font-size: 14px; }}
label {{ display: block; font-size: 14px; margin: 12px 0 4px; color: #6b7280; }}
input {{ width: 100%; box-sizing: border-box; font-size: 16px; padding: 12px 14px; border: 0; border-radius: 14px;
        background: #f4f5f9; color: #111827; }}
input:focus {{ outline: 2px solid #ff5a5f; }}
button {{ width: 100%; margin-top: 20px; padding: 14px; font-size: 16px; font-weight: 700; border: 0;
         border-radius: 999px; background: #ff5a5f; color: #fff; box-shadow: 0 6px 16px rgba(255,90,95,.35); }}
.err {{ color: #ef4444; font-size: 14px; margin-top: 12px; text-align: center; }}
</style></head><body>
<form method="post" action="/login">
  <h1>Трекер для двох</h1>
  <p>Витрати Олі й Марка</p>
  <label for="u">Логін</label><input id="u" name="username" autocomplete="username" autocapitalize="none" required>
  <label for="p">Пароль</label><input id="p" name="password" type="password" autocomplete="current-password" required>
  <input type="hidden" name="next" value="{escape(next_url)}">
  <button type="submit">Увійти</button>
  {f'<div class="err">{escape(error)}</div>' if error else ''}
</form></body></html>"""
        return Response(html, status=401 if error else 200, mimetype="text/html")

    def static_ui(self, path):
        name = path.rsplit("/", 1)[-1]
        types = {"simple.css": "text/css", "simple.js": "text/javascript", "report.css": "text/css"}
        if name not in types:
            return Response("Не знайдено.", status=404)
        return Response((UI / name).read_bytes(), mimetype=types[name])

    def can_change(self, request, slug, rest):
        """Чи можна цей запит пропустити: читати можна все, змінювати лише готівку з «+»."""
        if rest.split("/", 1)[0] in BLOCKED_PAGES:
            return False
        if request.method in ("GET", "HEAD"):
            return rest != "api/source"
        if rest not in ALLOWED_WRITES or slug in READ_ONLY_LEDGERS:
            return False
        if rest == "api/source_slice":
            # Виправити чи видалити можна лише запис, доданий з телефона (*-manual.beancount).
            if request.method == "PUT":
                body = request.get_data()
                request.environ["wsgi.input"] = io.BytesIO(body)  # тіло ще прочитає Fava
                data = json.loads(body or b"{}")
            else:
                data = request.args
            try:
                entry = self.fava.config["LEDGERS"][slug].get_entry(data.get("entry_hash", ""))
            except Exception:
                return False
            return entry.meta.get("filename", "").endswith("-manual.beancount")
        return True

    def with_ui(self, environ, user):
        """Відповідь Fava з доданим спрощеним виглядом (лише для повних HTML-сторінок)."""
        response = Response.from_app(self.fava, environ)
        if response.mimetype != "text/html" or "partial=" in environ.get("QUERY_STRING", ""):
            return response
        html = response.get_data(as_text=True)
        ledgers = json.dumps(USERS[user]["ledgers"], ensure_ascii=False)
        head = (f'<link rel="stylesheet" href="/ui/simple.css"><link rel="stylesheet" href="/ui/report.css">'
                f"<script>window.TRACKER_LEDGERS = {ledgers};</script>"
                f'<script defer src="/ui/simple.js"></script></head>')
        response.set_data(html.replace("</head>", head, 1))
        return response

    def home(self, user):
        return f"/{quote(USERS[user]['ledgers'][0])}/{REPORT}"

    def handle_login(self, request):
        if request.method == "GET":
            return self.login_page(next_url=request.args.get("next", ""))
        ip = request.headers.get("X-Real-IP") or request.remote_addr or "?"
        if self.locked(ip):
            return self.login_page("Забагато спроб. Зачекайте хвилину.")
        user = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        expected = self.passwords.get(user, "")
        if not expected or not hmac.compare_digest(password.encode(), expected.encode()):
            count, _ = self.fails.get(ip, (0, 0))
            self.fails[ip] = (count + 1, time.time())
            return self.login_page("Неправильний логін або пароль.")
        self.fails.pop(ip, None)
        next_url = request.form.get("next", "")
        # Лише внутрішні адреси, щоб посилання на вхід не перекидало на чужий сайт.
        if not next_url.startswith("/") or next_url.startswith("//") or urlparse(next_url).netloc:
            next_url = self.home(user)
        response = Response(status=303, headers={"Location": next_url})
        response.set_cookie(COOKIE, self.signer.dumps(user), max_age=SESSION_DAYS * 86400,
                            httponly=True, secure=not self.allow_http, samesite="Lax")
        return response

    # ---------- головний вхід ----------
    def __call__(self, environ, start_response):
        request = Request(environ)
        if not self.allow_http and not self.is_https(environ):
            url = "https://" + request.host + request.full_path.rstrip("?")
            return Response(status=301, headers={"Location": url})(environ, start_response)

        path = environ.get("PATH_INFO", "/").encode("latin-1").decode("utf-8", "replace")
        if path == "/login":
            response = self.handle_login(request)
        elif path == "/logout":
            response = Response(status=303, headers={"Location": "/login"})
            response.delete_cookie(COOKIE)
        else:
            user = self.user_from_cookie(request)
            first = path.strip("/").split("/", 1)[0]
            if user is None:
                response = Response(status=303, headers={
                    "Location": "/login?next=" + quote(request.full_path.rstrip("?"))})
            elif first in ("", "jump"):
                response = Response(status=303, headers={"Location": self.home(user)})
            elif first == "ui":
                response = self.static_ui(path)
            elif first == "static":
                response = self.fava
            elif first in USERS[user]["ledgers"]:
                rest = path.strip("/").split("/", 1)[1] if "/" in path.strip("/") else ""
                if self.can_change(request, first, rest):
                    response = self.with_ui(environ, user)
                else:
                    response = Response("Цю дію в трекері вимкнено.", status=403)
            else:
                response = Response("Немає доступу до цього обліку.", status=403)
        if response is not self.fava:
            response.headers["Cache-Control"] = "no-store"
        return response(environ, start_response)


application = Gate()

if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple("127.0.0.1", 5050, application, use_reloader=False)
