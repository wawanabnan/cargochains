# core/validators.py

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


# =========================
# BASIC IMAGE VALIDATORS
# =========================

ALLOWED_EXTS = {"png", "jpg", "jpeg"}
ALLOWED_MIMES = {"image/png", "image/jpeg"}


def validate_image_extension(value):
    """
    Validate by filename extension.
    Note: extension can be faked; keep MIME validation too.
    """
    name = (getattr(value, "name", "") or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_EXTS:
        raise ValidationError(
            f"Tipe file tidak diizinkan. Gunakan: {', '.join(sorted(ALLOWED_EXTS))}."
        )


def validate_image_mime(value):
    """
    Validate by uploaded content_type (browser-provided).
    Good enough for internal app; can be hardened further if needed.
    """
    content_type = (getattr(value, "content_type", "") or "").lower()
    if content_type and content_type not in ALLOWED_MIMES:
        raise ValidationError("File harus berupa image PNG atau JPEG.")


# =========================
# MIGRATION-SAFE VALIDATORS
# =========================

@deconstructible
class FileSizeValidator:
    """
    Migration-safe validator (no closures).
    max_mb: integer or float (e.g. 0.5 for 500KB, 1 for 1MB)
    """
    message = "Ukuran file maksimal {max} MB."

    def __init__(self, max_mb=1):
        self.max_mb = float(max_mb)
        self.max_bytes = int(self.max_mb * 1024 * 1024)

    def __call__(self, value):
        size = getattr(value, "size", None)
        if size is not None and size > self.max_bytes:
            raise ValidationError(self.message.format(max=self.max_mb))


@deconstructible
class ImageDimensionsValidator:
    """
    Optional: validate max width/height (px) using Pillow.
    Also migration-safe.
    """
    message = "Resolusi maksimal {w}x{h}px. Saat ini {cw}x{ch}px."

    def __init__(self, max_width=1200, max_height=600):
        self.max_width = int(max_width)
        self.max_height = int(max_height)

    def __call__(self, value):
        try:
            from PIL import Image
            # Ensure pointer at start for safety
            try:
                value.seek(0)
            except Exception:
                pass

            img = Image.open(value)
            w, h = img.size
        except Exception:
            raise ValidationError("File gambar tidak valid.")

        if w > self.max_width or h > self.max_height:
            raise ValidationError(
                self.message.format(w=self.max_width, h=self.max_height, cw=w, ch=h)
            )

        # Reset pointer for any later processing
        try:
            value.seek(0)
        except Exception:
            pass
