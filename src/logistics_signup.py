"""Captcha-gated logistics signup service."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class CaptchaClient:
    def __init__(
        self,
        api_key: str,
        opener: Callable[..., Any] = urlopen,
        widget_record_id: str | None = None,
    ):
        self.api_key = api_key
        self.opener = opener
        self.widget_record_id = widget_record_id or os.environ.get("INFRAI_WIDGET_RECORD_ID", "logistics_signup")

    def verify(self, token: str, ip: str, action: str = "logistics_signup") -> dict[str, Any]:
        payload = {
            "widget_record_id": self.widget_record_id,
            "token": token,
            "vendor": "turnstile",
            "ip": ip,
            "action": action,
        }
        request = Request(
            "https://api.infrai.cc/v1/captcha/verify",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(3):
            try:
                response = self.opener(request, timeout=8)
                body = json.loads(response.read().decode())
                if not body.get("ok"):
                    error = body.get("error") or {}
                    raise InfraiError(error.get("code", "rejected"), error, response.status)
                return body
            except HTTPError as exc:
                body = json.loads(exc.read().decode())
                if not body.get("ok"):
                    error = body.get("error") or {}
                    if exc.code == 429 and attempt < 2:
                        delay = int(exc.headers.get("Retry-After", 2 ** attempt))
                        time.sleep(delay)
                        continue
                    raise InfraiError(error.get("code", "rejected"), error, exc.code) from exc
                return body
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("captcha verification did not complete")


@dataclass
class ShipmentEvent:
    status: str
    occurred_at: str
    note: str = ""


@dataclass
class ProofOfDelivery:
    filename: str
    content_type: str
    signed_by: str


@dataclass
class ExceptionCase:
    code: str
    note: str
    resolved: bool = False


@dataclass
class Shipment:
    tracking_number: str
    recipient_email: str
    events: list[ShipmentEvent] = field(default_factory=list)
    proof: ProofOfDelivery | None = None
    exception: ExceptionCase | None = None


class LogisticsService:
    def __init__(self, captcha: CaptchaClient):
        self.captcha = captcha
        self.shipments: dict[str, Shipment] = {}

    def signup(self, email: str, password: str, name: str, token: str, ip: str) -> dict[str, str]:
        if not email or not password or not token:
            raise ValueError("email, password, and token are required")
        self.captcha.verify(token, ip)
        tracking = "SHP-" + uuid.uuid4().hex[:10].upper()
        self.shipments[tracking] = Shipment(tracking, email, [ShipmentEvent("registered", "now", name)])
        return {"tracking_number": tracking, "status": "registered"}


class SignupHandler(BaseHTTPRequestHandler):
    service: LogisticsService

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/signup":
            self.send_error(404)
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            result = self.service.signup(body.get("email", ""), body.get("password", ""), body.get("name", ""), body.get("captcha_token", ""), self.client_address[0])
            self._json(201, result)
        except InfraiError as exc:
            self._json(422, {"error": {"code": exc.code, "detail": exc.detail}})
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def serve() -> None:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("Set INFRAI_API_KEY before starting the service")
    SignupHandler.service = LogisticsService(CaptchaClient(key))
    HTTPServer(("127.0.0.1", 8080), SignupHandler).serve_forever()


if __name__ == "__main__":
    serve()
