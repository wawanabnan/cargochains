import urllib.parse
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.timezone import now


def build_tracking_urls(tracking_no: str, token: str | None = None) -> tuple[str, str]:
    """
    Return (tracking_url, track_home_url) using SITE_BASE_URL.
    """
    base = getattr(settings, "SITE_BASE_URL", "").rstrip("/")
    track_home_url = f"{base}/track/"
    tracking_url = f"{base}/track/{tracking_no}/"
    if token:
        tracking_url = f"{tracking_url}?t={token}"
    return tracking_url, track_home_url


def build_tracking_email_context(*, shipment, token: str | None = None,
                                 customer_ref: str = "-", service: str = "-",
                                 origin: str = "-", destination: str = "-",
                                 cargo_info: str = "-") -> dict:
    tracking_url, track_home_url = build_tracking_urls(shipment.tracking_no, token)
    return {
        "year": now().year,
        "logo_url": getattr(settings, "EMAIL_LOGO_URL", ""),
        "tracking_no": shipment.tracking_no,
        "tracking_url": tracking_url,
        "track_home_url": track_home_url,
        "customer_ref": customer_ref,
        "service": service,
        "origin": origin,
        "destination": destination,
        "cargo_info": cargo_info,
    }


def send_tracking_created_email(to_email: str, context: dict):
    """
    Send dual-language tracking email (plain text + HTML).
    """
    subject = f"Tracking Shipment Anda – {context.get('tracking_no', '')}".strip()

    text_body = render_to_string("emails/tracking_created_dual.txt", context)
    html_body = render_to_string("emails/tracking_created_dual.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[to_email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def build_whatsapp_message_dual(*, tracking_no: str, tracking_url: str, track_home_url: str) -> str:
    return (
        "Halo Bapak/Ibu,\n"
        "Shipment Anda sudah dibuat.\n\n"
        f"📦 Tracking Number: {tracking_no}\n"
        f"🔗 Link Tracking: {tracking_url}\n\n"
        "Simpan link ini untuk tracking shipment Anda.\n"
        f"Jika link tidak bisa dibuka, kunjungi {track_home_url} lalu masukkan Tracking Number di atas.\n\n"
        "---\n"
        "Dear Sir/Madam,\n"
        "Your shipment has been created.\n\n"
        f"📦 Tracking Number: {tracking_no}\n"
        f"🔗 Tracking Link: {tracking_url}\n\n"
        "Please save this link to track your shipment.\n"
        f"If the link can’t be opened, visit {track_home_url} and enter the Tracking Number above.\n"
    )


def build_whatsapp_deeplink(phone_e164: str, message: str) -> str:
    """
    phone_e164: e.g. '6281234567890'
    """
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{phone_e164}?text={encoded}"
