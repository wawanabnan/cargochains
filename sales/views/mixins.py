# sales/views/mixins.py
class UserToFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = getattr(self, "request", None) and self.request.user
        return kwargs
