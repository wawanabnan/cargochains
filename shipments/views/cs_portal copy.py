from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from shipments.models import Shipment
from shipments.services.public_token import make_public_token
from shipments.services.notifications import (
    build_whatsapp_message_dual,
    build_whatsapp_deeplink,
    send_tracking_created_email,
)


@login_required
def cs_public_link_page(request):
    """
    CS tool page: search by tracking_no OR JO number, then generate public tracking link.
    Semi-auto:
      - Generate Link (+ WA message/link)
      - Send Email (template dual language)
    """
    shipment = None
    result = None
    error = ""

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        # ======================
        # SEARCH
        # ======================
        if action == "search":
            q = (request.POST.get("tracking_no") or "").strip()
            if not q:
                error = "Tracking number / JO number wajib diisi."
            else:
                shipment = Shipment.objects.filter(tracking_no=q).first()
                if shipment is None:
                    shipment = Shipment.objects.filter(job_order__number=q).first()

                if shipment is None:
                    error = "Shipment tidak ditemukan (cek Tracking No / JO Number)."

        # ======================
        # GENERATE LINK (+ WA)
        # ======================
        elif action == "generate":
            shipment_id = request.POST.get("shipment_id")
            if not shipment_id:
                error = "shipment_id wajib ada untuk generate link."
            else:
                ttl_days = int(request.POST.get("ttl_days", "30"))
                ttl_days = max(1, min(ttl_days, 365))

                shipment = get_object_or_404(Shipment, pk=shipment_id)

                token = make_public_token(
                    shipment.tracking_no,
                    ttl_seconds=ttl_days * 24 * 3600
                )
                expires_at = timezone.now() + timedelta(days=ttl_days)

                base = request.build_absolute_uri("/").rstrip("/")
                tracking_url = f"{base}/track/{shipment.tracking_no}/?t={token}"
                track_home_url = f"{base}/track/"

                wa_msg = build_whatsapp_message_dual(
                    tracking_no=shipment.tracking_no,
                    tracking_url=tracking_url,
                    track_home_url=track_home_url,
                )

                phone_e164 = (request.POST.get("phone_e164") or "").strip()  # contoh: 62812xxxx
                wa_link = build_whatsapp_deeplink(phone_e164, wa_msg) if phone_e164 else ""

                result = {
                    "url": tracking_url,
                    "expires_at": expires_at,
                    "ttl_days": ttl_days,
                    "wa_msg": wa_msg,
                    "wa_link": wa_link,
                }

        # ======================
        # SEND EMAIL (semi-auto)
        # ======================
        elif action == "send_email":
            shipment_id = request.POST.get("shipment_id")
            to_email = (request.POST.get("to_email") or "").strip()
            tracking_url = (request.POST.get("tracking_url") or "").strip()

            if not shipment_id:
                error = "shipment_id wajib ada untuk kirim email."
            elif not to_email:
                error = "Email customer wajib diisi."
            else:
                shipment = get_object_or_404(Shipment, pk=shipment_id)

                base = request.build_absolute_uri("/").rstrip("/")
                track_home_url = f"{base}/track/"

                # kalau tracking_url tidak dikirim (belum generate), fallback tanpa token
                if not tracking_url:
                    tracking_url = f"{base}/track/{shipment.tracking_no}/"

                context = {
                    "year": timezone.now().year,
                    "logo_url": getattr(settings, "EMAIL_LOGO_URL", ""),
                    "tracking_no": shipment.tracking_no,
                    "tracking_url": tracking_url,
                    "track_home_url": track_home_url,

                    # tambahan info (kalau nanti sudah ada, isi dari JO/serializer)
                    "customer_ref": "-",
                    "service": "-",
                    "origin": "-",
                    "destination": "-",
                    "cargo_info": "-",
                }

                # kirim email
                send_tracking_created_email(to_email, context)

                # balikin result biar template bisa tampil status
                result = result or {}
                result.update({
                    "url": tracking_url,
                    "email_sent_to": to_email,
                })

        else:
            error = "Action tidak valid."

    return render(
        request,
        "shipments/public/public_link.html",
        {"shipment": shipment, "result": result, "error": error},
    )
