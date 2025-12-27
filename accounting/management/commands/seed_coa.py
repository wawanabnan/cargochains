from django.core.management.base import BaseCommand
from django.db import transaction

from accounting.models.chart import Account

COA = [
    # ASSET
    ("1101", "Cash - Petty Cash", "asset"),
    ("1102", "Bank - BCA", "asset"),
    ("1103", "Bank - Mandiri", "asset"),
    ("1104", "Bank - BNI", "asset"),
    ("1105", "Bank - Other", "asset"),
    ("1110", "Cash In Transit", "asset"),

    ("1201", "Account Receivable - Trade", "asset"),
    ("1202", "AR - Employee/Advance", "asset"),
    ("1203", "AR - Other", "asset"),
    ("1210", "Allowance for Doubtful Accounts", "asset"),

    ("1301", "Prepaid Expense", "asset"),
    ("1302", "Prepaid Insurance", "asset"),
    ("1303", "Prepaid Rent", "asset"),
    ("1310", "Deposit to Vendors", "asset"),

    ("1401", "Inventory - Packing Material", "asset"),
    ("1402", "Inventory - Others", "asset"),

    ("1501", "VAT In (PPN Masukan)", "asset"),
    ("1502", "PPh 21 Prepaid", "asset"),
    ("1503", "PPh 23 Prepaid", "asset"),
    ("1504", "PPh 4(2) Prepaid", "asset"),
    ("1505", "Other Tax Prepaid", "asset"),

    ("1601", "Fixed Asset - Vehicle", "asset"),
    ("1602", "Fixed Asset - Equipment", "asset"),
    ("1603", "Fixed Asset - Furniture", "asset"),
    ("1604", "Fixed Asset - Computer & IT", "asset"),
    ("1611", "Accum Dep - Vehicle", "asset"),
    ("1612", "Accum Dep - Equipment", "asset"),
    ("1613", "Accum Dep - Furniture", "asset"),
    ("1614", "Accum Dep - Computer & IT", "asset"),

    # LIABILITY
    ("2101", "Account Payable - Trade", "liability"),
    ("2102", "AP - Other", "liability"),

    ("2201", "Customer Deposit / Unearned Revenue", "liability"),

    ("2301", "VAT Out (PPN Keluaran)", "liability"),
    ("2302", "PPh 21 Payable", "liability"),
    ("2303", "PPh 23 Payable", "liability"),
    ("2304", "PPh 4(2) Payable", "liability"),
    ("2305", "Corporate Income Tax Payable", "liability"),

    ("2401", "Accrued Expense", "liability"),
    ("2402", "Accrued Salary", "liability"),
    ("2403", "Accrued Bonus/THR", "liability"),
    ("2404", "Accrued Freight/Carrier Cost", "liability"),

    ("2501", "Loan Payable - Bank", "liability"),
    ("2502", "Loan Payable - Other", "liability"),

    # EQUITY
    ("3101", "Capital / Paid-in Capital", "equity"),
    ("3201", "Retained Earnings", "equity"),
    ("3301", "Current Year Profit/Loss", "equity"),

    # INCOME
    ("4101", "Revenue - Ocean Freight", "income"),
    ("4102", "Revenue - Air Freight", "income"),
    ("4103", "Revenue - Trucking / Inland", "income"),
    ("4104", "Revenue - Customs Clearance", "income"),
    ("4105", "Revenue - Handling / THC / Port Charges", "income"),
    ("4106", "Revenue - Warehousing", "income"),
    ("4107", "Revenue - Door to Door Service", "income"),
    ("4108", "Revenue - Document / Admin Fee", "income"),
    ("4109", "Revenue - Other Services", "income"),

    ("4201", "Sales Discount", "income"),
    ("4202", "Sales Return/Adjustment", "income"),

    # COGS (EXPENSE)
    ("5101", "COGS - Ocean Freight Cost", "expense"),
    ("5102", "COGS - Air Freight Cost", "expense"),
    ("5103", "COGS - Trucking Cost", "expense"),
    ("5104", "COGS - Customs/Broker Cost", "expense"),
    ("5105", "COGS - Handling/THC/Port Cost", "expense"),
    ("5106", "COGS - Warehousing Cost", "expense"),
    ("5107", "COGS - Packing Material", "expense"),
    ("5108", "COGS - Survey/Inspection", "expense"),
    ("5109", "COGS - Other Direct Cost", "expense"),

    # OPEX (EXPENSE)
    ("6101", "Salary & Wages", "expense"),
    ("6102", "BPJS & Allowances", "expense"),
    ("6103", "Overtime", "expense"),
    ("6104", "Bonus/THR", "expense"),

    ("6201", "Rent Expense", "expense"),
    ("6202", "Electricity/Water", "expense"),
    ("6203", "Internet/Phone", "expense"),
    ("6204", "Office Supplies", "expense"),
    ("6205", "Maintenance Office", "expense"),

    ("6301", "Sales Commission", "expense"),
    ("6302", "Entertainment", "expense"),
    ("6303", "Advertising/Promotion", "expense"),
    ("6304", "Travel Sales", "expense"),

    ("6401", "Fuel", "expense"),
    ("6402", "Toll & Parking", "expense"),
    ("6403", "Travel & Accommodation", "expense"),
    ("6404", "Vehicle Maintenance", "expense"),

    ("6501", "Legal & Notary", "expense"),
    ("6502", "Accounting/Consulting", "expense"),
    ("6503", "Software Subscription", "expense"),
    ("6504", "Hosting/Server", "expense"),
    ("6505", "Domain/SSL", "expense"),

    ("6601", "Bank Charges", "expense"),
    ("6602", "Interest Expense", "expense"),
    ("6603", "FX Loss", "expense"),

    ("6701", "Depreciation - Vehicle", "expense"),
    ("6702", "Depreciation - Equipment", "expense"),
    ("6703", "Depreciation - Furniture", "expense"),
    ("6704", "Depreciation - Computer & IT", "expense"),

    ("6801", "Insurance Expense", "expense"),
    ("6802", "Training", "expense"),
    ("6803", "Donations", "expense"),
    ("6809", "Other Expense", "expense"),

    # Other income/expense (optional)
    ("7101", "Other Income", "income"),
    ("7601", "Other Expense", "expense"),
    ("7602", "FX Gain", "income"),
]


class Command(BaseCommand):
    help = "Seed Chart of Accounts (COA) for CargoChains Accounting"

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0

        for code, name, typ in COA:
            obj, is_created = Account.objects.update_or_create(
                code=code,
                defaults={"name": name, "type": typ, "is_active": True},
            )
            if is_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"COA seed done. created={created}, updated={updated}, total={len(COA)}"))
