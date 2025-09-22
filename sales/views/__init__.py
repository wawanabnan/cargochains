from .lists import quotation_list,order_list
from .adds import quotation_add_header, quotation_add_lines #quotation_add_lines_session 
from .details import quotation_detail,order_detail
from .edits import quotation_edit
from .actions import quotation_delete, quotation_change_status
from .actions import quotation_delete, quotation_change_status, quotation_generate_so,order_change_status
from .details import quotation_detail, order_detail, quotation_print, quotation_pdf,order_print, order_pdf



__all__ = [
    "quotation_list",
    "quotation_add_header",
    "quotation_add_lines",
 #   "quotation_add_line_session",
    "quotation_detail",
    "quotation_edit",
    "quotation_delete",
    "quotation_change_status",
    "quotation_generate_so",
    "order_change_status",
    "order_detail"
    "quotation_print",
    "quotation_pdf",
    "order_print",
    "order_pdf",
    
]
