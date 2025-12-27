from django import forms

class BootstrapSmallMixin:
    """
    Paksa semua widget Bootstrap 5 jadi ukuran -sm:
    - Select/SelectMultiple -> "form-select form-select-sm"
    - Input/Textarea (kecuali checkbox/radio/file) -> "form-control form-control-sm"
    Aman: tidak dobel class.
    """
  
    def _normalize_classes(self, widget, *, sm_class, base_class, extra_classes=None):
        cur = (widget.attrs.get("class") or "").split()

        # buang base & sm kalau nyangkut
        cur = [c for c in cur if c not in (base_class, sm_class)]

        # tambah sm
        cur.append(sm_class)

        # tambah custom class
        if extra_classes:
            for c in extra_classes.split():
                if c not in cur:
                    cur.append(c)

        widget.attrs["class"] = " ".join(cur).strip()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            w = field.widget

            # contoh: tandai field tertentu
            extra = None
            if name == "partner":
                extra = "js-partner"
            elif name == "quantity":
                extra = "js-num text-end"

            # SELECT
            if isinstance(w, (forms.Select, forms.SelectMultiple)):
                self._normalize_classes(
                    w,
                    sm_class="form-select-sm",
                    base_class="form-select",
                    extra_classes=extra,
                )

            # INPUT / TEXTAREA
            elif isinstance(w, (forms.TextInput, forms.NumberInput, forms.EmailInput,
                                forms.URLInput, forms.DateInput, forms.DateTimeInput,
                                forms.TimeInput, forms.Textarea, forms.PasswordInput)):
                self._normalize_classes(
                    w,
                    sm_class="form-control-sm",
                    base_class="form-control",
                    extra_classes=extra,
                )
