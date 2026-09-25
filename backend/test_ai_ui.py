"""Manual browser smoke test for the built Angular AI page.

Run: python backend/test_ai_ui.py
The normal unittest discovery skips this browser-only diagnostic.
"""

import functools
import http.server
import json
from pathlib import Path
import threading
import unittest

if __name__ != "__main__":
    raise unittest.SkipTest("manual built-UI browser diagnostic")

from playwright.sync_api import expect, sync_playwright


root = Path(__file__).resolve().parents[1] / "It-shop/dist/lt-shop/browser"


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] == "/ai-recommend":
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 0), functools.partial(Handler, directory=str(root))
)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_port}"

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(10000)
        errors = []
        requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        build = {
            "summary": "Recommended PC",
            "parts": [{"type": "CPU", "name": "Ryzen test CPU", "price": 9000}],
            "performance": {},
            "pros": [],
            "cons": [],
            "totalBudget": "30,000 ฿",
        }

        def api(route):
            request = route.request
            path = request.url.split("/api/", 1)[-1]
            if path == "ai/recommend":
                body = request.post_data_json
                requests.append(body)
                answer = "สเปคนี้เล่น Valorant ได้" if body["mode"] == "ask" else json.dumps(build)
                response = {"status": "success", "data": answer, "session_id": None}
            else:
                response = {"status": "success", "data": []}
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(response, ensure_ascii=False))

        page.route("**/api/**", api)
        page.goto(base + "/ai-recommend")
        page.locator(".ai-toolbar-actions button").nth(2).click()
        expect(page.get_by_role("dialog", name="AI Provider Settings")).to_be_visible()
        page.locator(".settings-panel .panel-close").click()

        page.locator(".usecase-btn").first.click()
        page.locator(".budget-btn").first.click()
        page.locator(".ai-card.glow-card .btn-ai-glow").first.click()
        expect(page.locator(".spec-question")).to_be_visible()
        page.locator(".spec-question textarea").fill("เล่น Valorant ได้ไหม")
        page.locator(".spec-question button").click()
        expect(page.locator(".spec-answer")).to_contain_text("Valorant")
        assert [body["mode"] for body in requests] == ["recommend", "ask"]
        assert "Ryzen test CPU" in requests[-1]["spec_context"]
        assert not errors, errors
        browser.close()
        print("PASS: settings dialog, recommendation, ask follow-up with build context")
finally:
    server.shutdown()
    server.server_close()
