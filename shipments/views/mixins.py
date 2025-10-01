
from django.contrib import messages

class MessageMixin:
    success = "Saved."
    def ok(self, request, msg=None):
        messages.success(request, msg or self.success)
