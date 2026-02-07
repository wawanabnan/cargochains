def job_order_print_context(jo):
    return {
        "job_order": jo,
        "jo": jo,
        "job": jo,
        "order_number": getattr(jo, "order_number", "") or getattr(jo, "ref_number", "") or "",
    }
