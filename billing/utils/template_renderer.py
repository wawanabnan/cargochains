from django.template import Context, Template
from billing.models.config import BillingConfig


def render_billing_text(template_string, invoice):
    """
    Render dynamic billing text using Django template engine.
    Available context:
        - invoice
        - job
        - customer
        - config
    """

    if not template_string:
        return ""

    config = BillingConfig.get_solo()

    context = Context({
        "invoice": invoice,
        "job": invoice.job_order,
        "customer": invoice.customer,
        "config": config,
    })

    template = Template(template_string)
    return template.render(context)