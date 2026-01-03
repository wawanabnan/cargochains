# core/utils/system_messages.py
from django.contrib import messages


class SystemMessage:
    @staticmethod
    def success(request, text, *, modal=True, context=None):
        messages.success(
            request,
            text,
            extra_tags=SystemMessage._tags("success", modal, context),
        )

    @staticmethod
    def error(request, text, *, modal=True, context=None):
        messages.error(
            request,
            text,
            extra_tags=SystemMessage._tags("error", modal, context),
        )

    @staticmethod
    def warning(request, text, *, modal=False, context=None):
        messages.warning(
            request,
            text,
            extra_tags=SystemMessage._tags("warning", modal, context),
        )

    @staticmethod
    def info(request, text, *, modal=False, context=None):
        messages.info(
            request,
            text,
            extra_tags=SystemMessage._tags("info", modal, context),
        )

    @staticmethod
    def _tags(level, modal, context):
        tags = [level]
        if modal:
            tags.append("modal")
        if context:
            tags.append(context)
        return " ".join(tags)
