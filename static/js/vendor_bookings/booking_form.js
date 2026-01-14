document.addEventListener("DOMContentLoaded", function () {
  // ======================================================
  // A) Transport toggle (tab Locations)
  // ======================================================
  function setLocationsVisible(yes) {
    const tabBtn = document.getElementById("tab-locations");
    const pane = document.getElementById("pane-locations");

    if (tabBtn && tabBtn.parentElement) tabBtn.parentElement.classList.toggle("d-none", !yes);
    if (pane) pane.classList.toggle("d-none", !yes);

    if (!yes) {
      const activePane = document.querySelector("#vbTabsContent .tab-pane.active");
      if (activePane && activePane.id === "pane-locations") {
        document.getElementById("tab-general")?.click();
      }
    }
  }

  const cb = document.getElementById("id_is_transport");
  if (cb) {
    setLocationsVisible(cb.checked);
    cb.addEventListener("change", () => setLocationsVisible(cb.checked));
  }

  // ======================================================
  // B) Helpers
  // ======================================================
  function detectPrefix() {
    const el = document.querySelector('input[id$="-TOTAL_FORMS"]');
    if (!el) return null;
    return el.id.replace(/^id_/, "").replace(/-TOTAL_FORMS$/, "");
  }

  function safeJSON(v) {
    if (!v) return {};
    try {
      return JSON.parse(v);
    } catch (e) {
      return {};
    }
  }

  // ======================================================
  // C) Auto-grow textarea (.auto-grow)
  // ======================================================
  function autoGrowTextarea(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
  }

  // grow saat user ngetik
  document.addEventListener("input", function (e) {
    if (e.target && e.target.classList.contains("auto-grow")) {
      autoGrowTextarea(e.target);
    }
  });

  // grow saat halaman load (value sudah ada)
  document.querySelectorAll("textarea.auto-grow").forEach(autoGrowTextarea);

  // ======================================================
  // D) Vendor Booking Lines Module (Schema Modal + Auto Desc)
  //    -> Ini POINT D yang 250 baris itu (digabung ke sini)
  // ======================================================
  window.VB = window.VB || {};

  (function (VB) {
    // ---------- master cost type meta from template ----------
    function getJSONScript(id) {
      const el = document.getElementById(id);
      if (!el) return [];
      try {
        return JSON.parse(el.textContent || "[]");
      } catch (e) {
        return [];
      }
    }

    const COST_TYPES_RAW = getJSONScript("vbCostTypesJson"); // pastikan template render json_script ini
    const COST_TYPE_MAP = {};
    (COST_TYPES_RAW || []).forEach((ct) => {
      COST_TYPE_MAP[String(ct.id)] = {
        id: ct.id,
        code: ct.code,
        name: ct.name,
        cost_group: ct.cost_group,
        service_type: ct.service_type,
      };
    });

    VB.costTypeMap = COST_TYPE_MAP;   // untuk akses internal & debug
    VB.costTypesRaw = COST_TYPES_RAW; // optional debug
    // ---------- schema definitions ----------
 
    const SCHEMA = {
      TRUCK: [
        { key: "truck_type", label: "Truck Type" },
        { key: "from", label: "From" },
        { key: "to", label: "To" },
        { key: "note", label: "Note", type: "textarea" },
      ],
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

      // ✅ PACKING (contoh: Peti Kayu Mesin)
      PACKING: [
        { key: "material", label: "Material (e.g. Wood)" },
        { key: "standard", label: "Standard (e.g. ISPM 15)" },
        { key: "dimension", label: "Dimension (e.g. 100x100x100)" },
        { key: "note", label: "Note", type: "textarea" },
      ],

      // ✅ FUMIGATION (contoh: Methyl Bromide + target date)
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



    //----------end of schema definitions--------

    //-----------resolve schema-------------------
    
  function resolveSchema(ct) {
      if (!ct) return "OTHER";

      // ✅ deteksi khusus via code (karena FUMIGATION service_type masih OTHER)
      if (ct.code === "FUMIGATION") return "FUMIGATION";

      // transport modes
      if (ct.service_type === "TRUCK") return "TRUCK";
      if (ct.service_type === "SEA") return "SEA";
      if (ct.service_type === "AIR") return "AIR";

      // ✅ packing mode
      if (ct.service_type === "PACKING") return "PACKING";

      // groups
      if (ct.cost_group === "PORT") return "PORT";
      if (ct.cost_group === "DOCUMENT") return "DOCUMENT";
      if (ct.cost_group === "WAREHOUSE") {
        return ct.code === "WAREHOUSE_STORAGE" ? "WH_STORAGE" : "WH_HANDLING";
      }

      return "OTHER";
    }


    //----------end of resolve schema--------------

    function renderFields(schemaKey, data) {
      const box = document.getElementById("vb-line-dynamic-fields");
      if (!box) return;

      box.innerHTML = "";
      const fields = SCHEMA[schemaKey] || SCHEMA.OTHER;

      fields.forEach((f) => {
        const val = data && data[f.key] ? String(data[f.key]) : "";
        const isTA = f.type === "textarea";
        const inputType = f.type === "date" ? "date" : "text";

        box.insertAdjacentHTML(
          "beforeend",
          `
          <div class="mb-2">
            <label class="form-label">${f.label}</label>
            ${
              isTA
                ? `<textarea class="form-control form-control-sm" rows="3" data-key="${f.key}">${val}</textarea>`
                : `<input type="${inputType}" class="form-control form-control-sm" data-key="${f.key}" value="${val}">`
            }
          </div>
        `
        );
      });
    }
//---------------build description----------------------
    function buildDescription(ct, details) {
      if (!ct) return "";

      const schema = resolveSchema(ct);

      if (schema === "TRUCK") {
        const truck = details.truck_type ? ` – ${details.truck_type}` : "";
        const route = (details.from || details.to)
          ? ` – ${(details.from || "").trim()} → ${(details.to || "").trim()}`
          : "";
        return `${ct.name}${truck}${route}`.trim();
      }

      if (schema === "SEA") {
        const route = (details.pol || details.pod)
          ? ` – ${(details.pol || "").trim()} → ${(details.pod || "").trim()}`
          : "";
        const vv = (details.vessel || details.voyage)
          ? ` – ${(details.vessel || "").trim()} ${(details.voyage || "").trim()}`.trimEnd()
          : "";
        return `${ct.name}${route}${vv}`.trim();
      }

      if (schema === "AIR") {
        const route = (details.origin || details.destination)
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

      return ct.name;
    }

//--------------end of build description--------------

    function buildDescription(ct, details) {
      if (!ct) return "";

      const schema = resolveSchema(ct);

      if (schema === "TRUCK") {
        const truck = details.truck_type ? ` – ${details.truck_type}` : "";
        const route =
          details.from || details.to ? ` – ${(details.from || "").trim()} → ${(details.to || "").trim()}` : "";
        return `${ct.name}${truck}${route}`.trim();
      }

      if (schema === "SEA") {
        const route =
          details.pol || details.pod ? ` – ${(details.pol || "").trim()} → ${(details.pod || "").trim()}` : "";
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

      return ct.name;
    }

    // ---------- active modal state ----------
    let ACTIVE = null;

    function openModalForRow(tr) {
      const costSel = tr.querySelector('select[name$="-cost_type"]');
      const detailsInput = tr.querySelector('input[name$="-details"]');
      const descEl = tr.querySelector('textarea[name$="-description"], input[name$="-description"]');

      if (!costSel || !detailsInput || !descEl) return;

      const ct = COST_TYPE_MAP[String(costSel.value)] || null;
      const details = safeJSON(detailsInput.value);

      const schemaKey = resolveSchema(ct);
      renderFields(schemaKey, details);

      ACTIVE = { tr, ct, costSel, detailsInput, descEl, schemaKey };

      const modalEl = document.getElementById("vbLineDetailModal");
      if (modalEl && window.bootstrap) {
        new bootstrap.Modal(modalEl).show();
      }
    }

    function saveModalToRow() {
      if (!ACTIVE) return;

      const details = safeJSON(ACTIVE.detailsInput.value);

      // collect dynamic fields
      document.querySelectorAll("#vb-line-dynamic-fields [data-key]").forEach((el) => {
        details[el.dataset.key] = el.value;
      });

      // save details JSON
      ACTIVE.detailsInput.value = JSON.stringify(details);

      // update description (readonly)
      ACTIVE.descEl.value = buildDescription(ACTIVE.ct, details);

      // auto-grow description if textarea has class auto-grow
      if (ACTIVE.descEl.classList && ACTIVE.descEl.classList.contains("auto-grow")) {
        autoGrowTextarea(ACTIVE.descEl);
      }

      const modalEl = document.getElementById("vbLineDetailModal");
      if (modalEl && window.bootstrap) {
        const inst = bootstrap.Modal.getInstance(modalEl);
        inst && inst.hide();
      }

      ACTIVE = null;
    }

    // Bind save button ONCE
    const saveBtn = document.getElementById("vb-line-detail-save");
    if (saveBtn && !saveBtn.dataset.bound) {
      saveBtn.dataset.bound = "1";
      saveBtn.addEventListener("click", saveModalToRow);
    }

    // ---------- public hooks ----------
    VB.rebindRow = function (row) {
      if (!row) return;

      // ensure textarea auto-grow on row
      row.querySelectorAll("textarea.auto-grow").forEach(autoGrowTextarea);

      // bind detail button once
      const btn = row.querySelector(".vb-line-detail-btn");
      if (btn && !btn.dataset.bound) {
        btn.dataset.bound = "1";
        btn.addEventListener("click", function () {
          openModalForRow(row);
        });
      }

      // optional: if cost_type changes, refresh description (basic)
      const costSel = row.querySelector('select[name$="-cost_type"]');
      const detailsInput = row.querySelector('input[name$="-details"]');
      const descEl = row.querySelector('textarea[name$="-description"], input[name$="-description"]');

      if (costSel && !costSel.dataset.bound_desc) {
        costSel.dataset.bound_desc = "1";
        costSel.addEventListener("change", function () {
          const ct = COST_TYPE_MAP[String(costSel.value)] || null;
          const details = safeJSON(detailsInput ? detailsInput.value : "{}");
          if (descEl) descEl.value = buildDescription(ct, details);
          if (descEl && descEl.classList && descEl.classList.contains("auto-grow")) autoGrowTextarea(descEl);
        });
      }
    };

    VB.init = function () {
      document.querySelectorAll("#lines-table tbody tr").forEach(VB.rebindRow);
    };
  })(window.VB);

  // Init rows existing after module loaded
  if (window.VB && typeof window.VB.init === "function") {
    window.VB.init();
  }

  // ======================================================
  // E) Add Line (guard supaya tidak double bind)
  //    Kalau insert_update_line.js sudah handle add row,
  //    block ini tidak akan ganggu karena kita set dataset flag.
  // ======================================================
  const btnAdd = document.getElementById("btn-add-line");
  const tbody = document.querySelector("#lines-table tbody");
  const tmpl = document.getElementById("empty-line-row");
  const prefix = detectPrefix();
  const totalForms = prefix ? document.getElementById(`id_${prefix}-TOTAL_FORMS`) : null;

  if (btnAdd && tbody && tmpl && totalForms) {
    if (!btnAdd.dataset.bound_addline) {
      btnAdd.dataset.bound_addline = "1";
      btnAdd.addEventListener("click", function () {
        const idx = parseInt(totalForms.value || "0", 10);
        const html = tmpl.innerHTML.replace(/__prefix__/g, String(idx));
        tbody.insertAdjacentHTML("beforeend", html);
        totalForms.value = String(idx + 1);

        const newRow = tbody.lastElementChild;
        if (!newRow) return;

        // ✅ modal/detail/autodesc + bind events per row
        if (window.VB && typeof window.VB.rebindRow === "function") {
          window.VB.rebindRow(newRow);
        }

        // ✅ taxes select2 (autocomplete) untuk row baru
        initTaxSelect2(newRow);

        // ✅ grow textarea (kalau ada)
        newRow.querySelectorAll("textarea.auto-grow").forEach(autoGrowTextarea);
      });

    }
  }


// ======================================================
// TAX SELECT2 INITIALIZER
// ======================================================
  function initTaxSelect2(root) {
  if (!window.jQuery || !jQuery.fn || typeof jQuery.fn.select2 !== "function") {
    console.warn("Select2 belum ter-load. Skip initTaxSelect2()");
    return;
  }

  const $root = root ? $(root) : $(document);

  $root.find(".js-tax-select2").each(function () {
    const $el = $(this);

    // sudah di-init?
    if ($el.data("select2")) return;

    const url = $el.data("ajax-url");
    if (!url) {
      console.warn("Tax select2: data-ajax-url kosong", this);
      return;
    }

    $el.select2({
      width: "100%",
      placeholder: $el.data("placeholder") || "Taxes",
      allowClear: true,

      ajax: {
        url: url,
        dataType: "json",
        delay: 250,
       
        data: function (params) {
          // kalau user ngetik -> search normal
          if (params.term !== undefined) {
            return { q: params.term || "" }; // term kosong -> minta list default
          }

          // preload selected ids HANYA SEKALI (untuk edit mode)
          if (!$el.data("vbPreloadDone")) {
            $el.data("vbPreloadDone", 1);
            return { "ids[]": $el.val() || [] };
          }

          // setelah preload, kalau open tanpa term -> tampilkan list default
          return { q: "" };
        },

        processResults: function (data) {
          return data; // {results:[{id,text,title}]}
        },
        cache: true,
      },

      // dropdown: tampil rate, tooltip dari title
      templateResult: function (item) {
        if (!item || !item.id) return item.text || "";
        const $span = $("<span>").text(item.text || "");
        if (item.title) $span.attr("title", item.title);
        return $span;
      },

      // selection: tampil rate
      templateSelection: function (item) {
        return (item && item.text) ? item.text : "";
      },

      escapeMarkup: function (m) { return m; },
    });

    // ======================================================
    // HARD STYLE APPLY (NO BORDER + BADGE) VIA JS
    // ======================================================
    function getContainer() {
      try {
        const inst = $el.data("select2");
        if (inst && inst.$container) return inst.$container;
      } catch (e) {}
      // fallback
      return $el.nextAll(".select2, .select2-container").first();
    }

    // ==============================
// UX: klik kolom TAX (td / selection) -> open select2 (anti kedip)
// - hanya 1 handler (di TD) biar tidak dobel open/close
// - pakai click + stopPropagation
// - open di tick berikutnya (setTimeout 0)
// ==============================
(function bindTaxCellOpen() {
  const $td = $el.closest("td");
  if (!$td.length) return;

  // bind sekali per TD
  if ($td.data("vbTaxTdBound")) return;
  $td.data("vbTaxTdBound", 1);

  $td.on("click", function (e) {
    // klik remove (x) biarkan normal (hapus chip)
    if ($(e.target).closest(".select2-selection__choice__remove").length) return;

    // kalau user klik dropdown results, jangan ganggu
    if ($(e.target).closest(".select2-dropdown").length) return;

    // kalau sudah open, jangan toggle (biar nggak kedip)
    const $c = (typeof getContainer === "function")
      ? getContainer()
      : $el.nextAll(".select2, .select2-container").first();

    if ($c && $c.length && $c.hasClass("select2-container--open")) return;

    e.preventDefault();
    e.stopPropagation();

    // open setelah event click selesai, supaya tidak langsung close
    setTimeout(function () {
      $el.select2("open");
    }, 0);
  });
})();


    function applyHardStyles() {
      const $c = getContainer();
      if (!$c || !$c.length) return;

      $c.addClass("tax-badge-container"); // tetap set class untuk debug

      // selection root (single/multiple)
      const $sel = $c.find(".select2-selection").first();
      $sel.css({
        border: "none",
        boxShadow: "none",
        outline: "none",
        background: "transparent",
        minHeight: "auto",
        padding: "0",
      });

      // hilangkan arrow kalau single
      $c.find(".select2-selection__arrow").css({ display: "none" });

      // inline search field (multiple)
      $c.find(".select2-search__field").css({
        fontSize: "0.75rem",
        marginTop: "2px",
      });

      // style chips (multiple)
      $c.find(".select2-selection__choice").each(function () {
        $(this).css({
          backgroundColor: "#0d6efd",
          color: "#fff",
          border: "none",
          borderRadius: "999px",
          padding: "2px 8px",
          fontSize: "0.75rem",
          lineHeight: "1.4",
          margin: "2px 4px 2px 0",
        });
      });

      // remove btn (x)
      $c.find(".select2-selection__choice__remove").css({
        color: "#fff",
        border: "none",
        background: "transparent",
        marginRight: "4px",
      });
      $c.find(".select2-selection__clear").css({ display: "none" });
      $c.find(".select2-clear").css({ display: "none" });
      $c.find(".select2-selection__choice__remove").css({ display: "inline-block" });

    }

    // apply sekali setelah init
    setTimeout(applyHardStyles, 0);

    // apply tiap select/unselect
    $el.on("select2:select select2:unselect", function () {
      setTimeout(function () {
        // tooltip untuk chips
        const data = $el.select2("data") || [];
        const $c = getContainer();
        const $choices = $c.find(".select2-selection__choice");
        $choices.each(function (i) {
          const item = data[i];
          if (item && item.title) $(this).attr("title", item.title);
        });

        // apply style lagi (chip baru kadang belum kena)
        applyHardStyles();
      }, 0);
    });

    // MutationObserver: kalau select2 bikin chip baru, kita style ulang
    (function observeChoices() {
      const $c = getContainer();
      if (!$c || !$c.length) return;

      const target = $c.find(".select2-selection").get(0);
      if (!target) return;

      const obs = new MutationObserver(function () {
        applyHardStyles();
      });
      obs.observe(target, { childList: true, subtree: true });
    })();
  });
}


  initTaxSelect2(document);
  

});
