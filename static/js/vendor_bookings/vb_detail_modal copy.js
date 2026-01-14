(function () {
  window.VB = window.VB || {};
  VB.activeRow = null;

  // -----------------------------
  // Helpers (ISO-aware)
  // -----------------------------
  function isoPretty(iso) {
    // untuk teks auto-desc: tampilkan dd/mm/yyyy
    return VB && VB.iso_to_ddmmyyyy ? VB.iso_to_ddmmyyyy(iso) : (iso || "");
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
    // sesuaikan selector kalau beda
    const el = tr.querySelector('select[name$="-cost_type"]');
    return el ? el.value : "";
  }

  function detectMode(tr, costTypeId, details) {
      // 1️⃣ Prioritas: details._mode (persist dari apply sebelumnya)
      const m = (details && details._mode) ? String(details._mode).toUpperCase() : "";
      if (m === "SEA" || m === "AIR" || m === "INLAND") return m;

      // 2️⃣ Meta dari backend (kalau ada)
      const ct = VB.costTypeMap ? VB.costTypeMap[String(costTypeId)] : null;
      const st = (ct?.service_type || "").toUpperCase();
      if (st === "SEA") return "SEA";
      if (st === "AIR") return "AIR";
      if (st === "TRUCK" || st === "INLAND") return "INLAND";

      // 3️⃣ Heuristik dari text option cost type (fallback)
      const sel = tr.querySelector('select[name$="-cost_type"]');
      const txt = sel?.selectedOptions?.[0]?.textContent?.toUpperCase?.() || "";
      if (txt.includes("SEA")) return "SEA";
      if (txt.includes("AIR")) return "AIR";
      if (txt.includes("TRUCK") || txt.includes("INLAND")) return "INLAND";

      // 4️⃣ Default
      return "SEA";
  }


  function applyModeUI(mode, costTypeId) {
    // title/subtitle
    const ct = VB.costTypeMap ? VB.costTypeMap[String(costTypeId)] : null;
    const ctName = ct?.name || "Line Details";

    setText("vbDetailModalTitle", `Transport Details — ${mode === "SEA" ? "Sea Freight" : mode === "AIR" ? "Air Freight" : "Inland Transportation"}`);
    setText("vbDetailModalSubtitle", ctName);

    // blocks
    show("vbBlockSea", mode === "SEA");
    show("vbBlockAir", mode === "AIR");
    show("vbBlockInland", mode === "INLAND");

    // schedule
    show("vbSchedulePair", mode !== "INLAND");
    show("vbScheduleSingle", mode === "INLAND");

    // labels route
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

//-----------------------------------------
// Tambahan
//-----------------------------------------
function findDetailsInputFromRow(tr) {
  if (!tr) return null;

  // anchor utama: description atau cost_type
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

  // cari global (karena hidden sering di luar <tr>)
  return document.querySelector(`input[name="${CSS.escape(detailsName)}"]`);
}




  // -----------------------------
  // LOAD details -> modal
  // -----------------------------
  function vbLoadModalFromDetails(details) {
    details = details || {};
    const sch = details.schedule || {};
    const route = details.route || {};
    const ref = details.ref || {};
    const sea = details.sea || {};
    const air = details.air || {};
    const inland = details.inland || {};

    // schedule: ISO -> dd/mm (tampilan)
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

  // -----------------------------
  // READ modal -> details (ISO stored)
  // -----------------------------
  function vbReadModalToDetails(mode) {
    const details = {};
    details.route = {
      from: document.getElementById("vbRouteFrom")?.value || "",
      to: document.getElementById("vbRouteTo")?.value || "",
    };

    details.ref = { no: document.getElementById("vbRefNo")?.value || "" };
    details.note = document.getElementById("vbNote")?.value || "";

    // schedule
    details.schedule = {};
    const etdDD = document.getElementById("vbETD")?.value || "";
    const etaDD = document.getElementById("vbETA")?.value || "";
    const pickDD = document.getElementById("vbPickupDate")?.value || "";

    details.schedule.etd = VB.ddmmyyyy_to_iso ? VB.ddmmyyyy_to_iso(etdDD) : "";
    details.schedule.eta = VB.ddmmyyyy_to_iso ? VB.ddmmyyyy_to_iso(etaDD) : "";
    details.schedule.pickup_date = VB.ddmmyyyy_to_iso ? VB.ddmmyyyy_to_iso(pickDD) : "";

    // mode-specific
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

    // simpan mode supaya kebaca saat reload (optional tapi enak)
    details._mode = mode;

    return details;
  }

  // -----------------------------
  // Validation ringan (modal only)
  // -----------------------------
  function vbValidate(mode, details) {
    const errs = [];

    // route selalu wajib minimal salah satu, idealnya both
    if (!details.route?.from) errs.push("Route: From wajib diisi.");
    if (!details.route?.to) errs.push("Route: To wajib diisi.");

    if (mode === "SEA") {
      // minimal carrier atau vessel biar masuk akal
      const s = details.sea || {};
      if (!s.carrier && !s.vessel) errs.push("Sea: isi minimal Carrier atau Vessel.");
      // ETD/ETA optional (opsional, tapi kalau diisi harus valid iso sudah)
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
    // tempatkan 1 alert kecil di modal body bagian atas (kalau belum ada)
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
    box.innerHTML = `<div class="fw-semibold mb-1">Periksa dulu:</div><ul class="mb-0 ps-3">${errs.map(e => `<li>${e}</li>`).join("")}</ul>`;
  }

  // -----------------------------
  // Auto-description (ISO-aware)
  // -----------------------------
  function buildAutoDescription(mode, costTypeId, details) {
    const ct = VB.costTypeMap ? VB.costTypeMap[String(costTypeId)] : null;
    const ctName = ct?.name || (mode === "SEA" ? "Sea Freight" : mode === "AIR" ? "Air Freight" : "Inland Transportation");

    const from = (details.route?.from || "").trim();
    const to = (details.route?.to || "").trim();
    const route = (from && to) ? `${from} → ${to}` : (from || to);

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
      ].filter(Boolean).join(" - ");
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
      ].filter(Boolean).join(" - ");
    }

    // INLAND
    const t = details.inland || {};
    const vendor = (t.vendor || "").trim();
    const vehicle = (t.vehicle || "").trim();
    const pickup = isoPretty(details.schedule?.pickup_date);

    return [
      ctName,
      route,
      vendor || vehicle,
      ref ? `REF ${ref}` : "",
      pickup ? `Pickup ${pickup}` : "",
    ].filter(Boolean).join(" - ");
  }

  function applyAutoDescToRow(row, suggestion) {
    const desc = row.querySelector('input[name$="-description"], textarea[name$="-description"]');
    if (!desc) return;

    const current = (desc.value || "").trim();
    const prevAuto = (desc.dataset.autoDesc || "").trim();
    const userEdited = !!desc.dataset.userEdited;

    // RULE: jangan timpa kalau user sudah edit manual
    if (userEdited && current && current !== prevAuto) return;

    // isi/refresh auto desc
    desc.value = suggestion;
    desc.dataset.autoDesc = suggestion;

    if (desc.tagName === "TEXTAREA") {
      desc.style.height = "auto";
      desc.style.height = desc.scrollHeight + "px";
    }
  }

  // -----------------------------
  // OPEN modal from button (data-bs-toggle handles show),
  // but we still need to PREPARE content before shown.
  // We'll hook "click" to set row + load data + apply UI.
  // -----------------------------
  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".vb-line-detail-btn");
    if (!btn) return;

    const tr = btn.closest("tr");
    if (!tr) return;

    VB.activeRow = tr;

    
    const costTypeId = pickCostTypeIdFromRow(tr);
    const mode = detectMode(tr, costTypeId, details);

    // parse hidden details
    const hidden = findDetailsInputFromRow(tr);

console.log("[VB MODAL OPEN]", {
  row: tr,
  detailsInputFound: !!hidden,
  detailsInputName: hidden ? hidden.name : null,
  detailsInputValue: hidden ? hidden.value : null,
});

    let details = {};
    try {
      details = hidden && hidden.value ? JSON.parse(hidden.value) : {};
    } catch (_) {
      details = {};
    }

    // apply UI mode first
    applyModeUI(mode, costTypeId);

    // load fields
    vbLoadModalFromDetails(details);

    // clear errors
    vbShowErrors([]);

    // NOTE: show modal handled by data-bs-toggle/target (already)
  });

  // -----------------------------
  // OK / Apply
  // -----------------------------
  document.getElementById("vbDetailApplyBtn")?.addEventListener("click", function () {
    const row = VB.activeRow;
    if (!row) return;

    const costTypeId = pickCostTypeIdFromRow(row);

    let prevDetails = {};
    try {
      const hidden = findDetailsInputFromRow(row);
      prevDetails = hidden && hidden.value ? JSON.parse(hidden.value) : {};
    } catch (_) {}

    const mode = detectMode(row, costTypeId, prevDetails);

    const details = vbReadModalToDetails(mode);

    // validate
    const errs = vbValidate(mode, details);
    vbShowErrors(errs);
    if (errs.length) return;

    // write to hidden JSON
    const hidden = findDetailsInputFromRow(row);
    if (!hidden) {
      alert("Details field tidak ditemukan. Silakan reload halaman.");
      return;
    }
    hidden.value = JSON.stringify(details);

    // auto description ISO-aware
    const suggestion = buildAutoDescription(mode, costTypeId, details);
    applyAutoDescToRow(row, suggestion);
      console.log("[VB MODAL APPLY] after", { valueAfter: hidden.value });

    // close
    bootstrap.Modal.getOrCreateInstance(document.getElementById("vbDetailModal")).hide();
  });
})();
