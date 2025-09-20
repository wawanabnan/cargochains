from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from sales.models import SalesQuotation
# import form yang sudah kamu buat
# from sales.forms import QuotationHeaderForm, QuotationLineForm

def quotation_add_header(request):
    """
    Step-1: form header quotation baru
    """
    # TODO: isi logic add header (sudah kamu punya)
    ...

def quotation_add_lines_manual(request, pk):
    """
    Step-2: form manual untuk input lines quotation
    """
    # TODO: isi logic lines manual (sudah kamu punya)
    ...

def quotation_edit(request, pk):
    """
    Form edit quotation (gabungan header + lines kalau perlu).
    """
    quotation = get_object_or_404(SalesQuotation, pk=pk)
    # TODO: reuse logic add_header/lines untuk mode edit
    ...
