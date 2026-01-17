
class CostGroup:
    INLAND = "INLAND"
    SEA = "SEA"
    AIR = "AIR"
    PORT = "PORT"
    PACKING = "PACKING"
    DOCUMENT = "DOCUMENT"
    WAREHOUSE = "WAREHOUSE"
    OTHER = "OTHER"

SYSTEM_GROUP_CHOICES = [
    (CostGroup.INLAND, "Inland"),
    (CostGroup.SEA, "Sea Freight"),
    (CostGroup.AIR, "Air Freight"),
    (CostGroup.PORT, "Customs Clearance"),
    (CostGroup.PACKING, "Packing / Lashing"),
    (CostGroup.DOCUMENT, "Documentation"),
    (CostGroup.WAREHOUSE, "Warehouse"),
    (CostGroup.OTHER, "Other"),
]
