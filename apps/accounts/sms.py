"""Sending the OTP. 'console' prints it (for your laptop); 'msg91' sends a real SMS."""
import json
import logging
import urllib.request

from django.conf import settings

log = logging.getLogger("kamkarao")


def send_otp(phone: str, code: str) -> bool:
    provider = settings.OTP_PROVIDER
    if provider == "msg91":
        return _send_msg91(phone, code)
    log.warning("OTP for %s is %s (console mode, no SMS sent)", phone, code)
    print(f"\n*** KamKarao OTP for {phone}: {code} ***\n", flush=True)
    return True


def _send_msg91(phone: str, code: str) -> bool:
    """MSG91 OTP API. Needs a DLT-approved template whose variable is ##OTP##."""
    url = (
        "https://control.msg91.com/api/v5/otp"
        f"?template_id={settings.MSG91_TEMPLATE_ID}&mobile=91{phone}&otp={code}"
    )
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={"authkey": settings.MSG91_AUTH_KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read() or b"{}")
            ok = body.get("type") == "success"
            if not ok:
                log.error("MSG91 refused OTP: %s", body)
            return ok
    except Exception:
        log.exception("MSG91 OTP send failed")
        return False
