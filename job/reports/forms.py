from django import forms
from partners.models import Partner  # customer model kamu (sesuaikan)
from job.models.job_orders import JobOrder      # sesuaikan


from django import forms

# Kalau belum mau pakai filter customer/status dulu, kita bikin minimal dulu biar tidak error.
class ProfitabilityFilterForm(forms.Form):
    job_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))


class COGSJournalFilterForm(forms.Form):
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    posted_only = forms.BooleanField(required=False, initial=True)
