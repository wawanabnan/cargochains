(function () {
  window.VB = window.VB || {};
  const VB = window.VB;

  // ---------- load cost types from <script id="vbCostTypesJson" type="application/json"> ----------
  function getJSONScript(id) {
    const el = document.getElementById(id);
    if (!el) return [];
    try {
      return JSON.parse(el.textContent || "[]");
    } catch (e) {
      console.warn("VB schema: invalid JSON script", id, e);
      return [];
    }
  }

  const COST_TYPES_RAW = getJSONScript("vbCostTypesJson");
  const COST_TYPE_MAP = {};
  (COST_TYPES_RAW || []).forEach((ct) => {
    COST_TYPE_MAP[String(ct.id)] = {
      id: ct.id,
      code: ct.code,
      name: ct.name,
      cost_group: ct.cost_group,
      // NOTE: service_type is legacy mirror of cost_group; DO NOT use for schema resolution.
      service_type: ct.service_type,
    };
  });

  VB.costTypeMap = COST_TYPE_MAP;
  VB.costTypesRaw = COST_TYPES_RAW; // optional debug

  // ---------- schema definitions ----------
  VB.SCHEMA = {
    // ===== INLAND (single schema for pickup & delivery) =====
    INLAND_TRUCKING: [
      {
        key: "vehicle_type",
        label: "Vehicle Type",
        type: "select",
        options: [
        
          ["PICKUP", "Pickup"],
          ["CDE", "CDE (Colt Diesel Engkel)"],
          ["CDD", "CDD (Colt Diesel Double)"],
          ["FUSO", "Fuso"],
          ["TRONTON", "Tronton"],
          ["WINGBOX", "Wingbox"],
          ["SEMI_TRAILER", "Semi Trailer"],
        ],
      },
      { key: "origin", label: "Origin / Pickup Location" },
      { key: "destination", label: "Destination / Dropoff Location" },

      // cargo detail (optional)
      { key: "item", label: "Cargo Item (optional)" },
      { key: "weight", label: "Weight (optional)" },
      { key: "weight_uom", label: "Weight UOM", type: "select", options: [["KG", "KG"], ["LB", "LB"]] },
      { key: "package_qty", label: "Package Qty (optional)" },
      { key: "package_type", label: "Package Type (optional)" },

      { key: "note", label: "Note", type: "textarea" },
    ],

    // ===== SEA / AIR / others =====
    SEA: [
      { key: "pol", label: "POL" },
      { key: "pod", label: "POD" },
      { key: "vessel", label: "Vessel" },
      { key: "voyage", label: "Voyage" },
      { key: "note", label: "Note", type: "textarea" },
    ],
    AIR: [
      { key: "origin", label: "Origin" },
      { key: "destination", label: "Destination" },
      { key: "airline", label: "Airline" },
      { key: "note", label: "Note", type: "textarea" },
    ],
    PORT: [
      { key: "terminal", label: "Terminal" },
      { key: "activity", label: "Activity (THC/Stevedoring/LOLO/etc)" },
      { key: "ref", label: "Reference No (optional)" },
      { key: "note", label: "Note", type: "textarea" },
    ],
    PACKING: [
      { key: "material", label: "Material (e.g. Wood)" },
      { key: "standard", label: "Standard (e.g. ISPM 15)" },
      { key: "dimension", label: "Dimension (e.g. 100x100x100)" },
      { key: "note", label: "Note", type: "textarea" },
    ],
    FUMIGATION: [
      { key: "chemical", label: "Chemical (e.g. Methyl Bromide)" },
      { key: "target_date", label: "Target Date", type: "date" },
      { key: "note", label: "Note", type: "textarea" },
    ],
    WH_HANDLING: [
      { key: "activity", label: "Handling Activity" },
      { key: "qty_info", label: "Qty Info (e.g. 20 pallets)" },
      { key: "note", label: "Note", type: "textarea" },
    ],
    WH_STORAGE: [
      { key: "duration", label: "Duration (e.g. 5 days)" },
      { key: "volume", label: "Volume/Unit (e.g. 20 pallets / 10 CBM)" },
      { key: "note", label: "Note", type: "textarea" },
    ],
    DOCUMENT: [
      { key: "doc_type", label: "Doc Type" },
      { key: "ref", label: "Reference No (PIB/BL/DO/etc)" },
      { key: "note", label: "Note", type: "textarea" },
    ],
    OTHER: [{ key: "note", label: "Note", type: "textarea" }],
  };

  // ---------- helpers ----------
  VB.getCostType = function getCostType(costTypeId) {
    return VB.costTypeMap[String(costTypeId || "")] || null;
  };

  /**
   * Cost-type-centric schema resolver.
   * IMPORTANT: DO NOT use ct.service_type (legacy mirror of cost_group).
   */
  VB.getSchemaKeyFromCostType = function getSchemaKeyFromCostType(ct) {
    if (!ct) return null;

    // special
    if (ct.code === "FUMIGATION") return "FUMIGATION";

    // INLAND trucking pickup/delivery share ONE schema
    if (ct.cost_group === "INLAND") {
      if (ct.code === "TRUCKING_PICKUP" || ct.code === "TRUCKING_DELIVERY") {
        return "INLAND_TRUCKING";
      }
      // future inland cost types can still use the same schema by default
      return "INLAND_TRUCKING";
    }

    // warehouse split
    if (ct.cost_group === "WAREHOUSE") {
      return ct.code === "WAREHOUSE_STORAGE" ? "WH_STORAGE" : "WH_HANDLING";
    }

    // group mapping
    if (ct.cost_group === "SEA") return "SEA";
    if (ct.cost_group === "AIR") return "AIR";
    if (ct.cost_group === "PORT") return "PORT";
    if (ct.cost_group === "DOCUMENT") return "DOCUMENT";
    if (ct.cost_group === "PACKING") return "PACKING";

    return "OTHER";
  };

  VB.resolveSchema = function resolveSchema(ct) {
    if (!ct) return "OTHER";
    const key = VB.getSchemaKeyFromCostType(ct);
    return key && VB.SCHEMA[key] ? key : "OTHER";
  };

  // ---------- auto description (single source of truth) ----------
  VB.buildDescription = function buildDescription(ct, details) {
    if (!ct) return "";
    details = details || {};

    const schema = VB.resolveSchema(ct);

    if (schema === "INLAND_TRUCKING") {
      const veh = details.vehicle_type ? ` – ${details.vehicle_type}` : "";
      const route =
        details.origin || details.destination
          ? ` – ${(details.origin || "").trim()} → ${(details.destination || "").trim()}`
          : "";
      const item = details.item ? ` – ${details.item}` : "";
      const w =
        details.weight
          ? ` (${details.weight}${details.weight_uom ? " " + details.weight_uom : ""})`
          : "";
      const pkg =
        details.package_qty || details.package_type
          ? ` – ${String(details.package_qty || "").trim()} ${String(details.package_type || "").trim()}`.trim()
          : "";
      return `${ct.name}${veh}${route}${item}${w}${pkg}`.replace(/\s+/g, " ").trim();
    }

    if (schema === "SEA") {
      const route =
        details.pol || details.pod
          ? ` – ${(details.pol || "").trim()} → ${(details.pod || "").trim()}`
          : "";
      const vv =
        details.vessel || details.voyage
          ? ` – ${(details.vessel || "").trim()} ${(details.voyage || "").trim()}`.trimEnd()
          : "";
      return `${ct.name}${route}${vv}`.trim();
    }

    if (schema === "AIR") {
      const route =
        details.origin || details.destination
          ? ` – ${(details.origin || "").trim()} → ${(details.destination || "").trim()}`
          : "";
      const airline = details.airline ? ` – ${details.airline}` : "";
      return `${ct.name}${route}${airline}`.trim();
    }

    if (schema === "PACKING") {
      const mat = details.material ? ` – ${details.material}` : "";
      const std = details.standard ? ` – ${details.standard}` : "";
      const dim = details.dimension ? ` (${details.dimension})` : "";
      return `${ct.name}${mat}${std}${dim}`.trim();
    }

    if (schema === "FUMIGATION") {
      const chem = details.chemical ? ` – ${details.chemical}` : "";
      const td = details.target_date ? ` – ${details.target_date}` : "";
      return `${ct.name}${chem}${td}`.trim();
    }

    if (schema === "WH_HANDLING") {
      const act = details.activity ? ` – ${details.activity}` : "";
      const qty = details.qty_info ? ` (${details.qty_info})` : "";
      return `Warehouse handling${act}${qty}`.trim();
    }

    if (schema === "WH_STORAGE") {
      const dur = details.duration ? ` – ${details.duration}` : "";
      const vol = details.volume ? ` (${details.volume})` : "";
      return `Warehouse storage${dur}${vol}`.trim();
    }

    if (schema === "PORT") {
      const term = details.terminal ? ` – ${details.terminal}` : "";
      const act = details.activity ? ` – ${details.activity}` : "";
      return `${ct.name}${term}${act}`.trim();
    }

    if (schema === "DOCUMENT") {
      const dt = details.doc_type ? ` – ${details.doc_type}` : "";
      const rf = details.ref ? ` – ${details.ref}` : "";
      return `${ct.name}${dt}${rf}`.trim();
    }

    return ct.name || "";
  };
})();
