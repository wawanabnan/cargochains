# shipments/services/vendor_booking_group.py

def get_vb_groups(vb):
    """
    Return list of distinct non-empty groups (uppercase) from VendorBookingLine.cost_group.
    """
    qs = (
        vb.lines.values_list("cost_group", flat=True)
        .exclude(cost_group__isnull=True)
        .exclude(cost_group__exact="")
        .distinct()
    )
    return [str(x).upper().strip() for x in qs if str(x).strip()]


def get_vb_group_strict(vb) -> str:
    """
    Return single group. Raise ValueError if mixed or missing.
    """
    groups = get_vb_groups(vb)
    if not groups:
        raise ValueError("Cost group kosong. Pastikan line memiliki cost_group.")
    if len(groups) > 1:
        raise ValueError(f"Cost group campur: {', '.join(groups)}. Satu Vendor Booking harus 1 group.")
    return groups[0]


# shipments/services/vendor_booking_group.py  (boleh taruh di sini juga)

GROUP_TO_DOCUMENT = {
    "SEA": "SHIPPING_INSTRUCTION",  # SI
    "AIR": "AIR_SLI",               # nanti
    "INLAND": "TRUCK_TO",           # nanti
}

def get_document_key_for_group(group: str) -> str | None:
    """
    Return document key for numbering / document creation, or None if no special document.
    """
    return GROUP_TO_DOCUMENT.get((group or "").upper().strip())
