import pytest

from src.logistics_signup import InfraiError, LogisticsService


class FakeCaptcha:
    def __init__(self, accepted):
        self.accepted = accepted

    def verify(self, token, ip):
        if not self.accepted:
            raise InfraiError("rejected", {"message": "rejected"}, 422)
        return {"ok": True, "data": {}}


def test_signup_creates_shipment_after_captcha():
    service = LogisticsService(FakeCaptcha(True))
    result = service.signup("ops@example.com", "secret", "Rin", "captcha-token", "127.0.0.1")
    assert result["status"] == "registered"
    assert result["tracking_number"] in service.shipments


def test_rejected_captcha_does_not_create_shipment():
    service = LogisticsService(FakeCaptcha(False))
    with pytest.raises(InfraiError):
        service.signup("ops@example.com", "secret", "Rin", "captcha-token", "127.0.0.1")
    assert service.shipments == {}
