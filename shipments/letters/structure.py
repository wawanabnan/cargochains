LETTER_STRUCTURE = {
  "SEA_SI": [
    {"title": "Reference", "fields": [
      {"name": "reference_no", "col": "col-md-6", "label": "B/L Number"},
    ]},
    {"title": "Route & Schedule", "fields": [
      {"name": "pol", "col": "col-md-3", "label": "POL"},
      {"name": "pod", "col": "col-md-3", "label": "POD"},
      {"name": "etd", "col": "col-md-3", "label": "ETD"},
      {"name": "eta", "col": "col-md-3", "label": "ETA"},
    ]},
    {"title": "Parties & Cargo", "fields": [
      {"name": "shipper_name", "col": "col-md-6", "label": "Shipper"},
      {"name": "consignee_name", "col": "col-md-6", "label": "Consignee"},
      {"name": "notify_party_name", "col": "col-md-6", "label": "Notify Party"},
      {"name": "cargo_information", "col": "col-md-12", "label": "Cargo Information"},
    ]},
  ],

  "AIR_SLI": [
    {"title": "Reference", "fields": [
      {"name": "reference_no", "col": "col-md-6", "label": "AWB Number"},
    ]},
    {"title": "Route & Schedule", "fields": [
      {"name": "origin_airport", "col": "col-md-6", "label": "Origin Airport"},
      {"name": "dest_airport", "col": "col-md-6", "label": "Destination Airport"},
      {"name": "etd", "col": "col-md-3", "label": "ETD"},
      {"name": "eta", "col": "col-md-3", "label": "ETA"},
    ]},
    {"title": "Parties & Cargo", "fields": [
      {"name": "shipper_name", "col": "col-md-6", "label": "Shipper"},
      {"name": "consignee_name", "col": "col-md-6", "label": "Consignee"},
      {"name": "notify_party_name", "col": "col-md-6", "label": "Notify Party"},
      {"name": "cargo_information", "col": "col-md-12", "label": "Cargo Information"},
    ]},
  ],

  "TRUCK_TO": [
    {"title": "Pickup / Delivery", "fields": [
      {"name": "pickup_location", "col": "col-md-6", "label": "Pickup Location"},
      {"name": "delivery_location", "col": "col-md-6", "label": "Delivery Location"},
      {"name": "pickup_date", "col": "col-md-3", "label": "Pickup Date"},
      {"name": "delivery_date", "col": "col-md-3", "label": "Delivery Date"},
    ]},
    {"title": "Parties & Cargo", "fields": [
      {"name": "shipper_name", "col": "col-md-6", "label": "Shipper"},
      {"name": "consignee_name", "col": "col-md-6", "label": "Consignee"},
      {"name": "notify_party_name", "col": "col-md-6", "label": "Notify Party"},
      {"name": "cargo_information", "col": "col-md-12", "label": "Cargo Information"},
    ]},
  ],
}

def get_letter_structure(letter_type: str):
  return LETTER_STRUCTURE.get(letter_type) or LETTER_STRUCTURE["TRUCK_TO"]
