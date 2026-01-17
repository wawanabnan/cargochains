(function () {
  window.VB = window.VB || {};
  const VB = window.VB;

  // =============================
// ID Number Utils (id-ID)
// - UI: 1.234,50
// - Stored: 1234.50
// =============================
const VBNumber = (() => {
  function parseIDNumber(v) {
    v = String(v ?? "").trim();
    if (!v) return "";
    // "1.234,56" -> "1234.56"
    return v.replace(/\./g, "").replace(",", ".");
  }

    function formatIDNumber(v, decimals = 2) {
      const s = String(v ?? "").trim();
      if (!s) return "";
      const n = Number(s);
      if (Number.isNaN(n)) return s;

      return n.toLocaleString("id-ID", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
    }

    function force(el, decimals = 2) {
      if (!el) return;
      const clean = parseIDNumber(el.value || "");
      if (!clean) return;
      el.value = formatIDNumber(clean, decimals); // -> "12,00" (id-ID)
    }


    function bindIDNumberFormat(inputId, decimals = 2) {
      const el = document.getElementById(inputId);
      if (!el) return;

      // ✅ klik/focus: select all, tanpa ubah value (tetap "12,50")
      el.addEventListener("focus", function () {
        requestAnimationFrame(() => {
          try { el.select(); } catch (e) {}
        });
      });

      // ✅ blur: format ke id-ID 2 desimal (mis. "12" -> "12,00")
      el.addEventListener("blur", function () {
        setTimeout(() => force(el, decimals), 0);
      });

      // optional: change untuk mobile
      el.addEventListener("change", function () {
        setTimeout(() => force(el, decimals), 0);
      });
    }


    // ✅ fallback global: kalau ada script lain yang overwrite, ini menang terakhir
    function bindGlobal(ids, decimals = 2) {
      document.addEventListener(
        "focusout",
        function (e) {
          const el = e.target;
          if (!el || !ids.includes(el.id)) return;
          setTimeout(() => force(el, decimals), 50);
        },
        true
      );
    }

    // panggil ini sekali untuk modal
    function bindModal() {
      bindIDNumberFormat("vbCargoWeight", 2);
      bindIDNumberFormat("vbCargoPkgQty", 2);

      // fallback kebal overwrite (optional tapi recommended)
      bindGlobal(["vbCargoWeight", "vbCargoPkgQty"], 2);
    }

    return {
      parse: parseIDNumber,
      format: formatIDNumber,
      bind: bindIDNumberFormat,
      bindModal,
    };
  })();


  VB.activeRow = null;

  // =============================
  // Helpers (ISO-aware)
  // =============================
  function isoPretty(iso) {
    if (VB && typeof VB.iso_to_ddmmyyyy === "function") return VB.iso_to_ddmmyyyy(iso);
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

  function parseJSONSafe(s) {
    if (!s) return {};
    try {
      const obj = JSON.parse(s);
      return obj && typeof obj === "object" ? obj : {};
    } catch (e) {
      return {};
    }
  }

  // ✅ Robust: derive hidden -details input dari anchor name
  function findDetailsInputFromRow(tr) {
    if (!tr) return null;

    const anchor =
      tr.querySelector('input[name$="-description"], textarea[name$="-description"]') ||
      tr.querySelector('input[name$="-cost_type"], select[name$="-cost_type"]');

    if (!anchor || !anchor.name) return null;

    let detailsName = "";
    if (anchor.name.endsWith("-description")) {
      detailsName = anchor.name.replace(/-description$/, "-details");
    } else if (anchor.name.endsWith("-cost_type")) {
      detailsName = anchor.name.replace(/-cost_type$/, "-details");
    }

    if (!detailsName) return null;

    // hidden bisa berada di luar <tr>
    return document.querySelector(`input[name="${CSS.escape(detailsName)}"]`);
  }

  function getCostTypeIdFromRow(tr) {
    const el =
      tr?.querySelector('input[name$="-cost_type"]') ||
      tr?.querySelector('select[name$="-cost_type"]');
    const v = el ? (el.value || "").trim() : "";
    return v || "";
  }

  function getCostTypeObjFromRow(tr) {
    const id = getCostTypeIdFromRow(tr);
    if (!id || !VB.getCostType) return null;
    return VB.getCostType(id);
  }

 
  function vbGetBookingGroupEl() {
  return (
    document.getElementById("id_booking_group") ||
    document.getElementById("id_cost_group") ||
    document.querySelector('[name="booking_group"]') ||
    document.querySelector('[name="cost_group"]')
  );
}

function vbRowHasCostType(tr) {
  const el =
    tr.querySelector('input[name$="-cost_type"]') ||
    tr.querySelector('select[name$="-cost_type"]');
  const v = el ? String(el.value || "").trim() : "";
  return !!v;
}

function vbAnyLineHasCostType() {
  return [...document.querySelectorAll("#lines-table tbody tr")]
    .some(tr => vbRowHasCostType(tr));
}


  function setDateLabels(mode) {
    const box = document.getElementById("vbSchedulePair");
    if (!box) return;

    const labels = Array.from(box.querySelectorAll("label"));
    if (!labels.length) return;

    const lblETD = labels.find((l) => /^(ETD|Pickup Date)$/i.test((l.textContent || "").trim()));
    const lblETA = labels.find((l) => /^(ETA|Delivery Date|Drop\s*\/\s*Delivery Date|Drop Date)$/i.test((l.textContent || "").trim()));

    if (mode === "INLAND") {
      if (lblETD) lblETD.textContent = "Pickup Date";
      if (lblETA) lblETA.textContent = "Drop / Delivery Date";
    } else {
      if (lblETD) lblETD.textContent = "ETD";
      if (lblETA) lblETA.textContent = "ETA";
    }
  }

function getBookingGroupMode() {
  const el = document.getElementById("id_booking_group");
  const g = el ? String(el.value || "").trim().toUpperCase() : "";
  if (g === "SEA" || g === "AIR" || g === "INLAND") return g;
  return "BASIC"; // semua group lain
}

  function applyModeUI(mode) {
    const title =
      mode === "SEA"
        ? "Transport Details — Sea Freight"
        : mode === "AIR"
        ? "Transport Details — Air Freight"
        : "Transport Details — Inland Trucking";

    const subtitle = mode === "SEA" ? "Sea Freight" : mode === "AIR" ? "Air Freight" : "Inland Trucking";

    setText("vbDetailModalTitle", title);
    setText("vbDetailModalSubtitle", subtitle);

    // blocks
    show("vbBlockSea", mode === "SEA");
    show("vbBlockAir", mode === "AIR");
    show("vbBlockInland", mode === "INLAND");


    const isTransport = (mode === "SEA" || mode === "AIR" || mode === "INLAND");
    show("vbSchedulePair", isTransport);
    show("vbScheduleSingle", false);


    show("vbRouteBox", isTransport); // jika ada wrapper id (kalau tidak ada, skip)
    show("vbRefBox", isTransport);   // 

    setText("vbLblRouteFrom", "Origin Location");
    setText("vbLblRouteTo", "Destination Location");
    
    const fromEl = document.getElementById("vbRouteFrom");
    const toEl = document.getElementById("vbRouteTo");

    if (fromEl && toEl) {
      if (mode === "SEA") {
        fromEl.placeholder = "Contoh: IDTPP (POL) / Tanjung Priok";
        toEl.placeholder = "Contoh: SGSIN (POD) / Singapore";
      } else if (mode === "AIR") {
        fromEl.placeholder = "Contoh: CGK (Origin Airport)";
        toEl.placeholder = "Contoh: SIN (Destination Airport)";
      } else {
        fromEl.placeholder = "Contoh: Jakarta / Warehouse A (singkat)";
        toEl.placeholder = "Contoh: Cikarang / Port / Airport (singkat)";
      }
    }


    // labels route + ref
   // ref label boleh tetap beda per mode (kalau om mau)
    if (mode === "SEA") {
        setText("vbLblRef", "B/L Number");
    } else if (mode === "AIR") {
        setText("vbLblRef", "AWB Number");
    } else {
      setText("vbLblRef", "Reference No");
     }

    setDateLabels(mode);

    if (document.getElementById("vbLblETD")) setText("vbLblETD", mode === "INLAND" ? "Pickup Date" : "ETD");
    if (document.getElementById("vbLblETA")) setText("vbLblETA", mode === "INLAND" ? "Delivery Date" : "ETA");
  }



  function parseIDNumber(v) {
  v = String(v ?? "").trim();
    if (!v) return "";
    // "1.234,56" -> "1234.56"
    return v.replace(/\./g, "").replace(",", ".");
  }

  function formatIDNumber(v, decimals = 2) {
    const s = String(v ?? "").trim();
    if (!s) return "";
    const n = Number(s);
    if (Number.isNaN(n)) return s;

    return n.toLocaleString("id-ID", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  function bindIDNumberFormat(inputId, decimals = 2) {
    const el = document.getElementById(inputId);
    if (!el) return;

    // saat focus: biarkan user edit dalam bentuk "clean"
    el.addEventListener("focus", function () {
      const v = el.value || "";
      const clean = parseIDNumber(v); // "1.234,50" -> "1234.50"
      el.value = clean;               // tampilkan versi edit-friendly
    });

    // saat blur: format ke id-ID 2 desimal
    el.addEventListener("blur", function () {
      const clean = parseIDNumber(el.value || "");
      if (!clean) {
        el.value = "";
        return;
      }
      el.value = formatIDNumber(clean, decimals); // -> "12,00"
    });
  }


  // =============================
  // LOAD details -> modal
  // =============================
  function vbLoadModalFromDetails(mode, details, tr) {

    details = details || {};
    const sch = details.schedule || {};
    const route = details.route || {};
    const ref = details.ref || {};
    const sea = details.sea || {};
    const air = details.air || {};
    const inland = details.inland || {};

    
    
    // schedule ISO -> dd/mm
    if (mode === "INLAND") {
      setVal("vbETD", VB.iso_to_ddmmyyyy ? VB.iso_to_ddmmyyyy(sch.pickup_date) : (sch.pickup_date || ""));
      setVal("vbETA", VB.iso_to_ddmmyyyy ? VB.iso_to_ddmmyyyy(sch.delivery_date) : (sch.delivery_date || ""));
    } else {
      setVal("vbETD", VB.iso_to_ddmmyyyy ? VB.iso_to_ddmmyyyy(sch.etd) : (sch.etd || ""));
      setVal("vbETA", VB.iso_to_ddmmyyyy ? VB.iso_to_ddmmyyyy(sch.eta) : (sch.eta || ""));
    }

    // route
    setVal("vbRouteFrom", route.from || "");
    setVal("vbRouteTo", route.to || "");

    // ref/note
    setVal("vbRefNo", ref.no || "");
    setVal("vbNote", details.note || "");


    const door = details.door || {};
    const pu = door.pickup || {};
    const dl = door.delivery || {};

    setVal("vbPickupName", pu.name || "");
    setVal("vbPickupAddr", pu.address || "");
    setVal("vbPickupCP", pu.contact_name || "");
    setVal("vbPickupPhone", pu.phone || "");

    setVal("vbDeliveryName", dl.name || "");
    setVal("vbDeliveryAddr", dl.address || "");
    setVal("vbDeliveryCP", dl.contact_name || "");
    setVal("vbDeliveryPhone", dl.phone || "");



    // sea
    setVal("vbSeaCarrier", sea.carrier || "");
    setVal("vbSeaVessel", sea.vessel || "");
    setVal("vbSeaVoyage", sea.voyage || "");

    // air
    setVal("vbAirAirline", air.airline || "");
    setVal("vbAirFlightNo", air.flight_no || "");

    // inland (new fields + backward compat)
    setVal("vbInlandActivity", inland.activity || "");
    setVal("vbInlandVehicleType", inland.vehicle_type || inland.vehicle || "");

    const cargo = inland.cargo || {};
    setVal("vbCargoItem", cargo.item || "");
    setVal("vbCargoWeightUom", cargo.weight_uom || "KG");
    setVal("vbCargoPkgType", cargo.package_type || "");
    setVal("vbCargoWeight", formatIDNumber(cargo.weight || "0"));
    setVal("vbCargoPkgQty", formatIDNumber(cargo.package_qty || "1", 2));

  // default uom (akan dioverride kalau ada value)
    setVal("vbCargoWeightUom", cargo.weight_uom || "KG");
    //console.log("RAW cargo.weight:", cargo.weight, "RAW cargo.package_qty:", cargo.package_qty);
    //console.log("FMT weight:", formatIDNumber(cargo.weight || "12.5", 2));
    //console.log("FMT qty:", formatIDNumber(cargo.package_qty || "1", 2));


    // auto activity from cost type if available
    const ct = getCostTypeObjFromRow(tr);
    if (mode === "INLAND" && ct && !String(inland.activity || "")) {
      if (ct.code === "TRUCKING_PICKUP") setVal("vbInlandActivity", "PICKUP");
      if (ct.code === "TRUCKING_DELIVERY") setVal("vbInlandActivity", "DELIVERY");
    }
  }

  // =============================
  // READ modal -> details (store ISO)
  // =============================
  function ddToISO(ddmmyyyy) {
    if (typeof VB.ddmmyyyy_to_iso === "function") return VB.ddmmyyyy_to_iso(ddmmyyyy);
    const m = String(ddmmyyyy || "").trim().match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (!m) return "";
    return `${m[3]}-${m[2]}-${m[1]}`;
  }

  document.addEventListener("focusout", (e) => {
    if (e.target && (e.target.id === "vbCargoWeight" || e.target.id === "vbCargoPkgQty")) {
      console.log("FOCUSOUT fired:", e.target.id, "value:", e.target.value);
    }
  });

  function vbReadModalToDetails(mode) {
    const details = {};
    if (mode === "BASIC") {
    details.note = document.getElementById("vbNote")?.value || "";
    details._mode = "BASIC";
    return details;
  }

    details.route = {
      from: document.getElementById("vbRouteFrom")?.value || "",
      to: document.getElementById("vbRouteTo")?.value || "",
    };

    details.ref = { no: document.getElementById("vbRefNo")?.value || "" };
    details.note = document.getElementById("vbNote")?.value || "";

    details.door = {
      pickup: {
        name: document.getElementById("vbPickupName")?.value || "",
        address: document.getElementById("vbPickupAddr")?.value || "",
        contact_name: document.getElementById("vbPickupCP")?.value || "",
        phone: document.getElementById("vbPickupPhone")?.value || "",
      },
      delivery: {
        name: document.getElementById("vbDeliveryName")?.value || "",
        address: document.getElementById("vbDeliveryAddr")?.value || "",
        contact_name: document.getElementById("vbDeliveryCP")?.value || "",
        phone: document.getElementById("vbDeliveryPhone")?.value || "",
      }
    };


    details.schedule = {};

    if (mode === "INLAND") {
      details.schedule.pickup_date = ddToISO(document.getElementById("vbETD")?.value || "");
      details.schedule.delivery_date = ddToISO(document.getElementById("vbETA")?.value || "");
    } else {
      details.schedule.etd = ddToISO(document.getElementById("vbETD")?.value || "");
      details.schedule.eta = ddToISO(document.getElementById("vbETA")?.value || "");
    }

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
        activity: document.getElementById("vbInlandActivity")?.value || "",
        vehicle_type: document.getElementById("vbInlandVehicleType")?.value || "",
        cargo: {
          item: document.getElementById("vbCargoItem")?.value || "",
          weight: document.getElementById("vbCargoWeight")?.value || "",
          weight_uom: document.getElementById("vbCargoWeightUom")?.value || "KG",
          package_qty: document.getElementById("vbCargoPkgQty")?.value || "",
          package_type: document.getElementById("vbCargoPkgType")?.value || "",
          
        },
      };
    }

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

    if (mode === "INLAND") {
      const p = details.schedule?.pickup_date || "";
      const d = details.schedule?.delivery_date || "";
      if (!p) errs.push("Inland: Pickup Date wajib diisi.");
      if (!d) errs.push("Inland: Delivery Date wajib diisi.");
      if (p && d && p > d) errs.push("Inland: Pickup Date tidak boleh lebih besar dari Delivery Date.");

      const t = details.inland || {};
      if (!t.vehicle_type) errs.push("Inland: Vehicle Type wajib dipilih.");

      return errs;
    }

    // SEA/AIR compare etd/eta
    const etd = details.schedule?.etd || "";
    const eta = details.schedule?.eta || "";
    if (etd && eta && etd > eta) errs.push("Schedule: ETD tidak boleh lebih besar dari ETA.");

    if (mode === "SEA") {
      const s = details.sea || {};
      if (!s.carrier && !s.vessel) errs.push("Sea: isi minimal Carrier atau Vessel.");
    } else if (mode === "AIR") {
      const a = details.air || {};
      if (!a.airline && !a.flight_no) errs.push("Air: isi minimal Airline atau Flight No.");
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
  // Auto-description (prefer VB.buildDescription if available)
  // =============================
  function buildAutoDescription(mode, details, tr) {
    const ct = getCostTypeObjFromRow(tr);

    // If vb_schema.js exists, prefer single source of truth there (it will use schema by ct)
    if (ct && typeof VB.buildDescription === "function") {
      // Convert our modal details to a flattened structure expected by vb_schema.js
      // For INLAND_TRUCKING in vb_schema.js, keys: vehicle_type, origin, destination, item, weight, weight_uom, package_qty, package_type
      const flat = {};
      if (mode === "INLAND") {
        flat.vehicle_type = details.inland?.vehicle_type || "";
        flat.origin = details.route?.from || "";
        flat.destination = details.route?.to || "";
        flat.item = details.inland?.cargo?.item || "";
        flat.weight = details.inland?.cargo?.weight || "";
        flat.weight_uom = details.inland?.cargo?.weight_uom || "";
        flat.package_qty = details.inland?.cargo?.package_qty || "";
        flat.package_type = details.inland?.cargo?.package_type || "";
        // we can append schedule text later
        const base = VB.buildDescription(ct, flat);
        const pickup = isoPretty(details.schedule?.pickup_date);
        const delivery = isoPretty(details.schedule?.delivery_date);
        const act = (details.inland?.activity || "").trim();
        const extra = [act, pickup ? `Pickup ${pickup}` : "", delivery ? `Delivery ${delivery}` : ""].filter(Boolean).join(" - ");
        return [base, extra].filter(Boolean).join(" - ");
      }
      // SEA/AIR keep old style
    }

    const ctName =
      (ct && ct.name) ||
      (mode === "SEA" ? "Sea Freight" : mode === "AIR" ? "Air Freight" : "Inland Trucking");

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

    // INLAND fallback
    const t = details.inland || {};
    const act = (t.activity || "").trim();
    const veh = (t.vehicle_type || "").trim();
    const pickup = isoPretty(details.schedule?.pickup_date);
    const delivery = isoPretty(details.schedule?.delivery_date);

    return [
      ctName,
      act,
      route,
      veh,
      ref ? `REF ${ref}` : "",
      pickup ? `Pickup ${pickup}` : "",
      delivery ? `Delivery ${delivery}` : "",
    ]
      .filter(Boolean)
      .join(" - ");
  }

  function applyAutoDescToRow(row, suggestion) {
    const desc = row.querySelector('input[name$="-description"], textarea[name$="-description"]');
    if (!desc) return;

    const current = (desc.value || "").trim();
    const prevAuto = (desc.dataset.autoDesc || "").trim();
    const userEdited = !!desc.dataset.userEdited;

    if (userEdited && current && current !== prevAuto) return;

    desc.value = suggestion;
    desc.dataset.autoDesc = suggestion;

    if (desc.tagName === "TEXTAREA") {
      desc.style.height = "auto";
      desc.style.height = desc.scrollHeight + "px";
    }
  }

  document.addEventListener("input", function (e) {
    const el = e.target;
    if (!el || !el.name) return;
    if (el.name.endsWith("-description")) el.dataset.userEdited = "1";
  });











  function setRowDescriptionFromModal(row) {
  const descBox = document.getElementById("vbLineDesc");
  const text = String(descBox ? descBox.value : "").trim();

  const rowDescEl =
    row.querySelector('input[name$="-description"]') ||
    row.querySelector('textarea[name$="-description"]');

  if (rowDescEl) {
    rowDescEl.value = text;
    rowDescEl.dataset.userEdited = "1";

    if (rowDescEl.tagName === "TEXTAREA") {
      rowDescEl.style.height = "auto";
      rowDescEl.style.height = rowDescEl.scrollHeight + "px";
    }
  }

  return text;
}

function setRowCostTypeFromPicker(row) {
  const wrap = document.getElementById("vbCtPickerWrap");
  const sel = document.getElementById("vbCostTypePick");

  // kalau picker tidak ada / tidak tampil, anggap OK
  if (!wrap || wrap.classList.contains("d-none") || !sel) return true;

  const picked = String(sel.value || "").trim();
  if (!picked) {
    vbShowErrors(["Cost Type wajib dipilih."]);
    sel.focus();
    return false;
  }

  const ctEl =
    row.querySelector('input[name$="-cost_type"]') ||
    row.querySelector('select[name$="-cost_type"]');

  if (ctEl) {
    ctEl.value = picked;
    ctEl.dispatchEvent(new Event("change", { bubbles: true }));
  }

  return true;
}

  // =============================
  // OPEN modal
  // =============================

    document.addEventListener("click", function (e) {
      const btn = e.target.closest(".vb-line-detail-btn");
      if (!btn) return;

      const tr = btn.closest("tr");
      if (!tr) return;

      VB.activeRow = tr;
      VBNumber.bindModal();

      const hidden = findDetailsInputFromRow(tr);
      const details = parseJSONSafe(hidden ? hidden.value : "{}");

      const mode = getBookingGroupMode();

      applyModeUI(mode);

      // ✅ Simple mode: hanya pakai textarea + cost type picker (tanpa schema transport)
      if (mode !== "BASIC") {
        vbLoadModalFromDetails(mode, details, tr);
      }

      // ✅ Prefill textarea description dari row
      const descBox = document.getElementById("vbLineDesc");
      const rowDescEl =
        tr.querySelector('input[name$="-description"]') ||
        tr.querySelector('textarea[name$="-description"]');
      if (descBox) descBox.value = rowDescEl ? (rowDescEl.value || "") : "";

      // ✅ Cost Type picker: isi sesuai booking_group (kalau helper VBQ tersedia)
      if (window.VBQ) {
        const group = VBQ.getBookingGroup();

        const wrap = document.getElementById("vbCtPickerWrap");
        const sel = document.getElementById("vbCostTypePick");
        const hint = document.getElementById("vbCtHint");

        // current cost_type dari row (kalau sudah ada)
        const ctEl =
          tr.querySelector('input[name$="-cost_type"]') ||
          tr.querySelector('select[name$="-cost_type"]');
        const currentId = ctEl ? (ctEl.value || "") : "";

        const r = VBQ.fillCostTypeSelect(sel, wrap, hint, group, currentId);

        // kalau hanya 1 pilihan → auto set ke row
        if (r && r.mode === "auto" && r.pickedId && ctEl) {
          ctEl.value = r.pickedId;
          ctEl.dispatchEvent(new Event("change", { bubbles: true }));
        }
      } else {
        console.warn("VBQ helper belum dimuat. Include vb_queries.js sebelum vb_detail_modal.js");
      }

       
      vbShowErrors([]);
    });

    
  // =============================
  // APPLY (OK)
  // =============================
    document.getElementById("vbDetailApplyBtn")?.addEventListener("click", function (e) {
  e.preventDefault();
  e.stopPropagation();

  const row = VB.activeRow;
  if (!row) return;

  const hidden = findDetailsInputFromRow(row);
  if (!hidden) {
    alert("Details field tidak ditemukan. Silakan reload halaman.");
    return;
  }

  vbShowErrors([]); // reset error

  // =============================
  // 1️⃣ VALIDASI COST TYPE (jika dropdown tampil)
  // =============================
  const wrap = document.getElementById("vbCtPickerWrap");
  const sel = document.getElementById("vbCostTypePick");

  let pickedCostType = "";

  if (wrap && !wrap.classList.contains("d-none") && sel) {
    pickedCostType = String(sel.value || "").trim();
    if (!pickedCostType) {
      vbShowErrors(["Cost Type wajib dipilih."]);
      sel.focus();
      return;
    }

    const ctEl =
      row.querySelector('input[name$="-cost_type"]') ||
      row.querySelector('select[name$="-cost_type"]');

    if (ctEl) {
      ctEl.value = pickedCostType;
      ctEl.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  // =============================
  // 2️⃣ VALIDASI DESCRIPTION (TEXTAREA)
  // =============================
  const descBox = document.getElementById("vbLineDesc");
  const desc = String(descBox ? descBox.value : "").trim();

  if (!desc) {
    vbShowErrors(["Description / quotation vendor wajib diisi."]);
    descBox?.focus();
    return;
  }

  // copy ke row description
  const rowDescEl =
    row.querySelector('input[name$="-description"]') ||
    row.querySelector('textarea[name$="-description"]');

  if (rowDescEl) {
    rowDescEl.value = desc;
    rowDescEl.dataset.userEdited = "1";

    if (rowDescEl.tagName === "TEXTAREA") {
      rowDescEl.style.height = "auto";
      rowDescEl.style.height = rowDescEl.scrollHeight + "px";
    }
  }

  // =============================
  // 3️⃣ SIMPAN DETAILS (SIMPLE)
  // =============================
  const details = {
    _mode: "BASIC",
    cost_type: pickedCostType || null,
    note: desc, // isi quotation vendor
  };

  hidden.value = JSON.stringify(details);

  // =============================
  // 4️⃣ TUTUP MODAL
  // =============================
  const modalEl = document.getElementById("vbDetailModal");
  if (modalEl && window.bootstrap && bootstrap.Modal) {
    bootstrap.Modal.getOrCreateInstance(modalEl).hide();
  }
});




})();
