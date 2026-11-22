import os
import socket
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET_KEY"] = "browser-e2e-secret-key-with-at-least-32-bytes"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
_E2E_DIR = Path(tempfile.mkdtemp(prefix="securecode-browser-e2e-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_E2E_DIR / 'app.db'}"

import uvicorn
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from securecode.adapters.postgres.models import Base, User
from securecode.api.app import app
from securecode.api.security import hash_password

_USERNAME = "browser.e2e@example.com"
_PASSWORD = "BrowserE2E#2026"


def _seed_user() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(User(
        id=uuid4(),
        username=_USERNAME,
        password_hash=hash_password(_PASSWORD),
        active=True,
        role="platform_admin",
        created_at=datetime.now(UTC),
    ))
    session.commit()
    session.close()
    engine.dispose()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    _seed_user()
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("El servidor E2E no inició")

    base_url = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            page.goto(f"{base_url}/app")
            assert page.evaluate("localStorage.getItem('securecode_token')") is None

            page.click("#btnOpenLogin")
            page.fill("#authUsername", _USERNAME)
            page.fill("#authPassword", _PASSWORD)
            with page.expect_response(
                lambda response: response.url.endswith("/api/v1/auth/session")
                and response.request.method == "POST"
            ) as login_info:
                page.click("#loginForm button[type='submit']")
            assert login_info.value.status == 200

            page.wait_for_function(
                "() => { const button = document.getElementById('btnLogout'); return button && !button.hidden; }"
            )
            assert page.evaluate("localStorage.getItem('securecode_token')") is None
            assert page.evaluate("document.querySelector('#userProfileName').textContent") == _USERNAME

            cookies = {cookie["name"]: cookie for cookie in context.cookies()}
            assert cookies["securecode_session"]["httpOnly"] is True
            assert cookies["securecode_session"]["sameSite"] == "Lax"
            assert cookies["securecode_csrf"]["httpOnly"] is False
            csrf_token = cookies["securecode_csrf"]["value"]

            unsafe_url = f"{base_url}/api/v1/auth/logout"
            without_csrf = context.request.post(unsafe_url, headers={"Origin": base_url})
            assert without_csrf.status == 403
            with_wrong_origin = context.request.post(
                unsafe_url,
                headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf_token},
            )
            assert with_wrong_origin.status == 403

            with page.expect_response(
                lambda response: response.url.endswith("/api/v1/auth/logout")
                and response.request.method == "POST"
            ) as logout_info:
                page.click("#btnLogout")
            assert logout_info.value.status == 204
            page.wait_for_function(
                "() => { const button = document.getElementById('btnLogout'); return button && button.hidden; }"
            )
            assert context.request.get(f"{base_url}/api/v1/auth/me").status == 401
            assert not errors, errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)

    print(f"E2E navegador OK: {_E2E_DIR}")


if __name__ == "__main__":
    main()
