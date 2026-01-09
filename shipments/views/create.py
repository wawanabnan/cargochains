from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.shortcuts import redirect
from django.views.generic import CreateView

from shipments.models.shipments import Shipment
from shipments.forms.shipment_create import ShipmentCreateForm
from core.utils.numbering import get_next_number
from partners.models import PartnerRole, PartnerRoleTypes


def ensure_partner_role(partner, role_code: str):
    if not partner:
        return
    role_type = PartnerRoleTypes.objects.filter(code=role_code).first()
    if not role_type:
        return
    PartnerRole.objects.get_or_create(
        partner=partner,
        role_type=role_type,
    )


class ShipmentCreateView(LoginRequiredMixin, CreateView):
    model = Shipment
    form_class = ShipmentCreateForm
    template_name = "shipments/shipment_form.html"

    def get_success_url(self):
        return reverse("shipments:detail", args=[self.object.pk])

    def form_valid(self, form):
        shipment: Shipment = form.save(commit=False)

        # nomor & status PLAN
        if not shipment.number:
            shipment.number = get_next_number("SHIPMENT")
        shipment.status = Shipment.STATUS_PLAN

        if hasattr(shipment, "created_by") and self.request.user.is_authenticated:
            shipment.created_by = self.request.user

        shipment.save()

        # set partner role otomatis
        ensure_partner_role(shipment.customer, "CUSTOMER")
        ensure_partner_role(shipment.shipper, "SHIPPER")
        ensure_partner_role(shipment.consignee, "CONSIGNEE")

        self.object = shipment
        return redirect(self.get_success_url())
