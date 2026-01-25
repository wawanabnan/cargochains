from django import forms

class SelectMultipleWithDataCode(forms.SelectMultiple):
    def __init__(self, *args, code_map=None, **kwargs):
        self.code_map = code_map or {}
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value is not None:
            code = self.code_map.get(str(value))
            if code:
                option["attrs"]["data-code"] = code
        return option
