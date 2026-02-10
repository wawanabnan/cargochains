from django.contrib import messages
from django.utils.html import format_html, format_html_join


def flash_errors(request, errors, *, title="Ada error", level="error", max_items=3):
    """
    Render errors as ONE bootstrap-friendly HTML message.
    """
    errors = [e for e in (errors or []) if str(e).strip()]
    shown = errors[:max_items]
    remaining = max(0, len(errors) - len(shown))

    items_html = format_html_join("", "<li>{}</li>", ((e,) for e in shown))
    more_html = format_html("<li>+{} error lain</li>", remaining) if remaining else ""

    html = format_html(
        "<div class='fw-semibold mb-1'>{}</div><ul class='mb-0 ps-3'>{}{}</ul>",
        title, items_html, more_html
    )

    if level == "warning":
        messages.warning(request, html)
    elif level == "success":
        messages.success(request, html)
    elif level == "info":
        messages.info(request, html)
    else:
        messages.error(request, html)
