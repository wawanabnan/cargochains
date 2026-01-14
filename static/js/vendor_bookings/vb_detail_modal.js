/* static/vendor_bookings/vb_detail_modal.js
   Controller untuk Vendor Booking Line Detail Modal (SEA / AIR / INLAND)
   - Open modal: prepare UI + load details
   - OK/Apply: validate ringan + simpan JSON (ISO) ke hidden -details + auto-description
   - Robust untuk Django formset: hidden -details bisa berada di luar <tr>
*/
(function () {
  window.VB = window.VB || {};
  VB.activeRow = null;

  // =============================
  // Helpers (ISO-aware)
  // =============================
  function isoPretty(iso) {
    // ISO -> dd/mm/yyyy (buat auto-description)
    if (window.VB && typeof VB.iso_to_ddmmyyyy === "function") return VB.iso_to_ddmmyyyy(iso);
    return iso || "";
  }

  function setText(id, v) {
    const el = document.getElementById(id);
    if (el) el.textContent = v || "";
  }

  function setVal(id, v) {
    const el = document.getElementById(id);
    if (el) el.value = v || "";
  }

  function show(id, yes) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("d-none", !yes);
  }

  function pickCostTypeIdFromRow(tr) {
    const el = tr ? tr.querySelector('select[name$="-cost_type"]') : null;
    return el ? (el.value || "") : "";
  }

  // ✅ Robust: derive input hidden -details dari anchor name (description/cost_type)
  function findDetailsInputFromRow(tr) {
    if (!tr) return null;

    const anchor =
      tr.querySelector('input[name$="-description"], textarea[name$="-description"]') ||
      tr.querySelector('select[name$="-cost_type"]');

    if (!anchor || !anchor.name) return null;

    let detailsName = "";
    if (anchor.name.endsWith("-description")) {
      detailsName = anchor.name.replace(/-description$/, "-details");
    } else if (anchor.name.endsWith("-cost_type")) {
      detailsName = anchor.name.replace(/-cost_type$/, "-details");
    }

    if (!detailsName) return null;

    // hidden bisa berada di luar <tr> → cari global
    return document.querySelector(`input[name="${CSS.escape(detailsName)}"]`);
  }

  function parseJSONSafe(s) {
    if (!s) return {};
    try {
      const obj = JSON.parse(s);
      return obj && typeof obj === "object" ? obj : {};
    } catch (e) {
      return {};
    }
  }

  // =============================
  // Mode detection (SEA/AIR/INLAND)
  // Priority: details._mode -> VB.costTypeMap -> option text heuristik -> default SEA
  // =============================
  function detectMode(tr, costTypeId, details) {
    const m = details && details._mode ? String(details._mode).toUpperCase() : "";
    if (m === "SEA" || m === "AIR" || m === "INLAND") return m;

    const ct = VB.costTypeMap ? VB.costTypeMap[String(costTypeId)] : null;
    const st = (ct?.service_type || "").toUpperCase();
    if (st === "SEA") return "SEA";
    if (st === "AIR") return "AIR";
    if (st === "TRUCK" || st === "INLAND") return "INLAND";

    const sel = tr ? tr.querySelector('select[name$="-cost_type"]') : null;
    const txt = sel?.selectedOptions?.[0]?.textContent?.toUpperCase?.() || "";
    if (txt.includes("SEA")) return "SEA";
    if (txt.includes("AIR")) return "AIR";
    if (txt.includes("TRUCK") || txt.includes("INLAND")) return "INLAND";

    return "SEA";
  }

  function applyModeUI(mode, costTypeId) {
    const ct = VB.costTypeMap ? VB.costTypeMap[String(costTypeId)] : null;
    const ctName = ct?.name || "—";

    const title =
      mode === "SEA"
        ? "Transport Details — Sea Freight"
        : mode === "AIR"
        ? "Transport Details — Air Freight"
        : "Transport Details — Inland Transportation";

    setText("vbDetailModalTitle", title);
    setText("vbDetailModalSubtitle", ctName);

    // blocks
    show("vbBlockSea", mode === "SEA");
    show("vbBlockAir", mode === "AIR");
    show("vbBlockInland", mode === "INLAND");

    // schedule
    show("vbSchedulePair", mode !== "INLAND");
    show("vbScheduleSingle", mode === "INLAND");

    // labels route + ref
    if (mode === "SEA") {
      setText("vbLblRouteFrom", "POL (From Port)");
      setText("vbLblRouteTo", "POD (To Port)");
      setText("vbLblRef", "B/L Number");
    } else if (mode === "AIR") {
      setText("vbLblRouteFrom", "From (Airport)");
      setText("vbLblRouteTo", "To (Airport)");
      setText("vbLblRef", "AWB Number");
    } else {
      setText("vbLblRouteFrom", "Pickup Location");
      setText("vbLblRouteTo", "Dropoff Location");
      setText("vbLblRef", "DO / Reference No");
    }
  }

  // =============================
  // LOAD details -> modal (ISO -> dd/mm for display)
  // =============================
  function vbLoadModalFromDetails(details) {
    details = details || {};
    const sch = details.schedule || {};
    const route = details.route || {};
    const ref = details.ref || {};
    const sea = details.sea || {};
    const air = details.air || {};
    const inland = details.inland || {};

    // schedule ISO -> dd/mm
    setVal("vbETD", VB.iso_to_ddmmyyyy ? VB.iso_to_ddmmyyyy(sch.etd) : (sch.etd || ""));
    setVal("vbETA", VB.iso_to_ddmmyyyy ? VB.iso_to_ddmmyyyy(sch.eta) : (sch.eta || ""));
    setVal("vbPickupDate", VB.iso_to_ddmmyyyy ? VB.iso_to_ddmmyyyy(sch.pickup_date) : (sch.pickup_date || ""));

    // route
    setVal("vbRouteFrom", route.from || "");
    setVal("vbRouteTo", route.to || "");

    // ref/note
    setVal("vbRefNo", ref.no || "");
    setVal("vbNote", details.note || "");

    // sea
    setVal("vbSeaCarrier", sea.carrier || "");
    setVal("vbSeaVessel", sea.vessel || "");
    setVal("vbSeaVoyage", sea.voyage || "");

    // air
    setVal("vbAirAirline", air.airline || "");
    setVal("vbAirFlightNo", air.flight_no || "");

    // inland
    setVal("vbInlandVendor", inland.vendor || "");
    setVal("vbInlandVehicle", inland.vehicle || "");
  }

  // =============================
  // READ modal -> details (store ISO)
  // =============================
  function ddToISO(ddmmyyyy) {
    if (typeof VB.ddmmyyyy_to_iso === "function") return VB.ddmmyyyy_to_iso(ddmmyyyy);
    // fallback: kalau helper belum ada
    const m = String(ddmmyyyy || "").trim().match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (!m) return "";
    return `${m[3]}-${m[2]}-${m[1]}`;
  }

  function vbReadModalToDetails(mode) {
    const details = {};

    details.route = {
      from: document.getElementById("vbRouteFrom")?.value || "",
      to: document.getElementById("vbRouteTo")?.value || "",
    };

    details.ref = { no: document.getElementById("vbRefNo")?.value || "" };
    details.note = document.getElementById("vbNote")?.value || "";

    details.schedule = {};
    details.schedule.etd = ddToISO(document.getElementById("vbETD")?.value || "");
    details.schedule.eta = ddToISO(document.getElementById("vbETA")?.value || "");
    details.schedule.pickup_date = ddToISO(document.getElementById("vbPickupDate")?.value || "");

    if (mode === "SEA") {
      details.sea = {
        carrier: document.getElementById("vbSeaCarrier")?.value || "",
        vessel: document.getElementById("vbSeaVessel")?.value || "",
        voyage: document.getElementById("vbSeaVoyage")?.value || "",
      };
    } else if (mode === "AIR") {
      details.air = {
        airline: document.getElementById("vbAirAirline")?.value || "",
        flight_no: document.getElementById("vbAirFlightNo")?.value || "",
      };
    } else {
      details.inland = {
        vendor: document.getElementById("vbInlandVendor")?.value || "",
        vehicle: document.getElementById("vbInlandVehicle")?.value || "",
      };
    }

    // persist mode (biar konsisten ketika dibuka ulang)
    details._mode = mode;

    return details;
  }

  // =============================
  // Validation ringan (modal only)
  // =============================
  function vbValidate(mode, details) {
    const errs = [];

    if (!details.route?.from) errs.push("Route: From wajib diisi.");
    if (!details.route?.to) errs.push("Route: To wajib diisi.");

    const etd = details.schedule?.etd || "";
    const eta = details.schedule?.eta || "";
    if ((mode === "SEA" || mode === "AIR") && etd && eta && etd > eta) {
      errs.push("Schedule: ETD tidak boleh lebih besar dari ETA.");
    }

    if (mode === "SEA") {
      const s = details.sea || {};
      if (!s.carrier && !s.vessel) errs.push("Sea: isi minimal Carrier atau Vessel.");
    } else if (mode === "AIR") {
      const a = details.air || {};
      if (!a.airline && !a.flight_no) errs.push("Air: isi minimal Airline atau Flight No.");
    } else {
      const t = details.inland || {};
      if (!details.schedule?.pickup_date) errs.push("Inland: Pickup Date wajib diisi.");
      if (!t.vendor && !t.vehicle) errs.push("Inland: isi minimal Vendor atau Vehicle.");
    }

    return errs;
  }

  function vbShowErrors(errs) {
    let box = document.getElementById("vbDetailErrors");
    if (!box) {
      const body = document.querySelector("#vbDetailModal .modal-body");
      if (!body) return;
      box = document.createElement("div");
      box.id = "vbDetailErrors";
      box.className = "alert alert-danger py-2 small d-none";
      body.prepend(box);
    }

    if (!errs || !errs.length) {
      box.classList.add("d-none");
      box.innerHTML = "";
      return;
    }

    box.classList.remove("d-none");
    box.innerHTML =
      `<div class="fw-semibold mb-1">Periksa dulu:</div>` +
      `<ul class="mb-0 ps-3">${errs.map((e) => `<li>${e}</li>`).join("")}</ul>`;
  }

  // =============================
  // Auto-description (ISO-aware)
  // =============================
  function buildAutoDescription(mode, costTypeId, details) {
    const ct = VB.costTypeMap ? VB.costTypeMap[String(costTypeId)] : null;
    const ctName =
      ct?.name || (mode === "SEA" ? "Sea Freight" : mode === "AIR" ? "Air Freight" : "Inland Transportation");

    const from = (details.route?.from || "").trim();
    const to = (details.route?.to || "").trim();
    const route = from && to ? `${from} → ${to}` : (from || to);

    const ref = (details.ref?.no || "").trim();

    if (mode === "SEA") {
      const s = details.sea || {};
      const carrier = (s.carrier || "").trim();
      const vessel = (s.vessel || "").trim();
      const voyage = (s.voyage || "").trim();
      const etd = isoPretty(details.schedule?.etd);
      const eta = isoPretty(details.schedule?.eta);

      return [
        ctName,
        route,
        carrier || vessel,
        voyage ? `VY ${voyage}` : "",
        ref ? `BL ${ref}` : "",
        etd ? `ETD ${etd}` : "",
        eta ? `ETA ${eta}` : "",
      ]
        .filter(Boolean)
        .join(" - ");
    }

    if (mode === "AIR") {
      const a = details.air || {};
      const airline = (a.airline || "").trim();
      const flight = (a.flight_no || "").trim();
      const etd = isoPretty(details.schedule?.etd);
      const eta = isoPretty(details.schedule?.eta);

      return [
        ctName,
        route,
        airline,
        flight ? `FL ${flight}` : "",
        ref ? `AWB ${ref}` : "",
        etd ? `ETD ${etd}` : "",
        eta ? `ETA ${eta}` : "",
      ]
        .filter(Boolean)
        .join(" - ");
    }

    // INLAND
    const t = details.inland || {};
    const vendor = (t.vendor || "").trim();
    const vehicle = (t.vehicle || "").trim();
    const pickup = isoPretty(details.schedule?.pickup_date);

    return [ctName, route, vendor || vehicle, ref ? `REF ${ref}` : "", pickup ? `Pickup ${pickup}` : ""]
      .filter(Boolean)
      .join(" - ");
  }

  function applyAutoDescToRow(row, suggestion) {
    const desc = row.querySelector('input[name$="-description"], textarea[name$="-description"]');
    if (!desc) return;

    const current = (desc.value || "").trim();
    const prevAuto = (desc.dataset.autoDesc || "").trim();
    const userEdited = !!desc.dataset.userEdited;

    // RULE:
    // - kalau user pernah edit manual dan current != prevAuto → jangan timpa
    if (userEdited && current && current !== prevAuto) return;

    desc.value = suggestion;
    desc.dataset.autoDesc = suggestion;

    if (desc.tagName === "TEXTAREA") {
      desc.style.height = "auto";
      desc.style.height = desc.scrollHeight + "px";
    }
  }

  // Tandai manual edit description (biar auto-desc tidak menimpa)
  document.addEventListener("input", function (e) {
    const el = e.target;
    if (!el || !el.name) return;
    if (el.name.endsWith("-description")) el.dataset.userEdited = "1";
  });

  // =============================
  // OPEN modal: prepare UI + load row details
  // NOTE: modal show sudah di-handle oleh data-bs-toggle/data-bs-target
  // =============================
  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".vb-line-detail-btn");
    if (!btn) return;

    const tr = btn.closest("tr");
    if (!tr) return;

    VB.activeRow = tr;

    const costTypeId = pickCostTypeIdFromRow(tr);

    const hidden = findDetailsInputFromRow(tr);
    const details = parseJSONSafe(hidden ? hidden.value : "{}");

    const mode = detectMode(tr, costTypeId, details);

    applyModeUI(mode, costTypeId);
    vbLoadModalFromDetails(details);
    vbShowErrors([]);
  });

  // =============================
  // APPLY (OK): validate + save JSON + auto-desc + close
  // =============================
  document.getElementById("vbDetailApplyBtn")?.addEventListener("click", function () {
    const row = VB.activeRow;
    if (!row) return;

    const costTypeId = pickCostTypeIdFromRow(row);

    // ambil existing details (buat detectMode via _mode)
    const hidden = findDetailsInputFromRow(row);
    if (!hidden) {
      alert("Details field tidak ditemukan. Silakan reload halaman.");
      return;
    }

    const prevDetails = parseJSONSafe(hidden.value);
    const mode = detectMode(row, costTypeId, prevDetails);

    const details = vbReadModalToDetails(mode);

    const errs = vbValidate(mode, details);
    vbShowErrors(errs);
    if (errs.length) return;

    hidden.value = JSON.stringify(details);

    const suggestion = buildAutoDescription(mode, costTypeId, details);
    applyAutoDescToRow(row, suggestion);

    // close modal
    const modalEl = document.getElementById("vbDetailModal");
    if (modalEl && window.bootstrap && bootstrap.Modal) {
      bootstrap.Modal.getOrCreateInstance(modalEl).hide();
    }
  });
})();
