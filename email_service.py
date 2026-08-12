import os
import requests as http_requests

# ── Config from environment ─────────────────────────────────────────────
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
RESEND_URL = "https://api.resend.com/emails"

def send_notification_email(subject: str, html_body: str) -> bool:
    """
    Send an email notification via Resend HTTP API.
    """
    if not RESEND_API_KEY or not ADMIN_EMAIL:
        print("⚠️ Resend API key or admin email not configured. Skipping email.")
        return False

    try:
        payload = {
            "from": "RayBot <onboarding@resend.dev>",
            "to": [ADMIN_EMAIL],
            "subject": subject,
            "html": html_body,
        }

        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        }

        resp = http_requests.post(RESEND_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()

        print(f"✅ Notification email sent: {subject}")
        return True

    except Exception as e:
        print(f"❌ Error sending email via Resend: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response details: {e.response.text}")
        return False
