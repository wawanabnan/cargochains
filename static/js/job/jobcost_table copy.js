(function () {
  // ---------- helper format angka ID ----------
  function parseID(v) {
    if (!v) return 0;
    let s = String(v).trim();
    if (s.indexOf(",") >= 0) s = s.replace(/\./g, "").replace(",", ".");
    const n = parseFloat(s);
    return isNaN(n) ? 0 : n;
  }

  function fmtID(n) {
    return Number(n || 0).toLocaleString("id-ID", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  // ---------- detect prefix formset ----------
  function detectPrefix() {
    const el = document.querySelector('input[id^="id_"][id$="-TOTAL_FORMS"]');
    if (!el) return null;
    return el.id.replace(/^id_/, "").replace(/-TOTAL_FORMS$/, "");
  }

  // ---------- COST TYPE META (DB-driven) ----------
  function getCostTypeMeta(costTypeId) {
    const map = window.COST_TYPE_META || {};
    return map[String(costTypeId)] || null;
  }

  function vendorModeFromCostType(selectEl) {
    if (!selectEl) return true;
    const ctId = selectEl.value;
    if (!ctId) return true;
    const meta = getCostTypeMeta(ctId);
    if (!meta) return true;
    return !!meta.requires_vendor;
  }

  function applyCostTypeMode(row, prefix) {
    const ct =
      row.querySelector(`select[name^="${prefix}-"][name$="-cost_type"]`) ||
      row.querySelector('select[name$="-cost_type"]');

    const vw = row.querySelector(".js-vendor-wrap");
    const nw = row.querySelector(".js-internal-note-wrap");
    if (!vw || !nw) return;

    const vendorMode = vendorModeFromCostType(ct);

    if (vendorMode) {
      vw.classList.remove("d-none");
      nw.classList.add("d-none");
      const noteInput = nw.querySelector("input, textarea, select");
      if (noteInput) noteInput.value = "";
    } else {
      vw.classList.add("d-none");
      const vendorSel = vw.querySelector("select");
      if (vendorSel) vendorSel.value = "";
      nw.classList.remove("d-none");
    }
  }

  // ---------- money bind ----------
  function bindMoneyInput(el) {
    if (!el) return;
    if (el.type === "hidden" || el.disabled) return;
    if (el.dataset.moneyInit === "1") return;
    el.dataset.moneyInit = "1";

    el.addEventListener("focus", () => setTimeout(() => el.select(), 0));
    const format = () => { el.value = fmtID(parseID(el.value)); };
    el.addEventListener("blur", format);
    el.addEventListener("change", format);
    format();
  }

  // ---------- attach row handlers ----------
  function attachRow(row, prefix) {
    const est = row.querySelector(`input[name^="${prefix}-"][name$="-est_amount"]`);
    const act = row.querySelector(`input[name^="${prefix}-"][name$="-actual_amount"]`);

    bindMoneyInput(est);
    bindMoneyInput(act);

    // delete
    const btn = row.querySelector(".remove-row");
    const del = row.querySelector(`input[name^="${prefix}-"][name$="-DELETE"]`);
    if (btn && del && !btn.dataset.delInit) {
      btn.dataset.delInit = "1";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        del.checked = true;
        row.classList.add("d-none");
      });
    }

    applyCostTypeMode(row, prefix);
  }

  // ======================================================
  // EXPORT GLOBAL: initJobCostTable()
  // ======================================================
  window.initJobCostTable = function initJobCostTable() {
    const prefix = detectPrefix();
    const tbody = document.getElementById("jobcost-body");
    const addBtn = document.getElementById("btn-jobcost-add");
    const tpl = document.getElementById("jobcost-empty-row");

    if (!prefix) {
      console.warn("Formset prefix not found. Pastikan management_form ter-render.");
      return;
    }

    const totalForms = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    if (!tbody || !addBtn || !tpl || !totalForms) return;

    // init existing
    tbody.querySelectorAll("tr.jobcost-row").forEach(row => attachRow(row, prefix));

    // delegate change cost_type (bind once)
    if (!tbody.dataset.ctDelegateInit) {
      tbody.dataset.ctDelegateInit = "1";
      tbody.addEventListener("change", function (e) {
        const el = e.target;
        if (!el) return;
        if (
          el.matches(`select[name^="${prefix}-"][name$="-cost_type"]`) ||
          el.matches('select[name$="-cost_type"]')
        ) {
          const row = el.closest(".jobcost-row");
          if (row) applyCostTypeMode(row, prefix);
        }
      });
    }

    // add row (bind once)
    if (!addBtn.dataset.addInit) {
      alerrt("TEST");
      addBtn.dataset.addInit = "1";
      addBtn.addEventListener("click", function (e) {
        e.preventDefault();

        const idx = parseInt(totalForms.value || "0", 10);

        const html = tpl.innerHTML.replace(/__prefix__/g, idx).trim();

        const wrap = document.createElement("tbody");
        wrap.innerHTML = html;
        const row = wrap.querySelector("tr.jobcost-row") || wrap.querySelector("tr");
        if (!row) return;

        tbody.appendChild(row);
        totalForms.value = idx + 1;

        const touched = document.getElementById("jobcost-touched");
        if (touched) {
          alert("touched");

        }else{
          alert("not toucher");
        }

        // ✅ penting: jangan isi "0,00" otomatis, biar row baru dianggap kosong kalau user belum isi
        const est = row.querySelector(`input[name="${prefix}-${idx}-est_amount"]`);
        const act = row.querySelector(`input[name="${prefix}-${idx}-actual_amount"]`);
        if (est) est.value = "";
        if (act) act.value = "";

        // pastikan cost_type default kosong kalau ada empty option
        const ct = row.querySelector(`select[name="${prefix}-${idx}-cost_type"]`);
        if (ct) ct.value = "";

        attachRow(row, prefix);
      });
    }
  };
  
   function parseID(v) {
    if (!v) return 0;
    let s = String(v).trim();
    if (s.indexOf(",") >= 0) s = s.replace(/\./g, "").replace(",", ".");
    const n = parseFloat(s);
    return isNaN(n) ? 0 : n;
  }

  function fmtID(n) {
    return Number(n || 0).toLocaleString("id-ID", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  // ---------- detect prefix formset ----------
  function detectPrefix() {
    const el = document.querySelector('input[id^="id_"][id$="-TOTAL_FORMS"]');
    if (!el) return null;
    return el.id.replace(/^id_/, "").replace(/-TOTAL_FORMS$/, "");
  }

  // ---------- COST TYPE META (DB-driven) ----------
  function getCostTypeMeta(costTypeId) {
    const map = window.COST_TYPE_META || {};
    return map[String(costTypeId)] || null;
  }

  // ---------- vendor/non-vendor mode ----------
  function vendorModeFromCostType(selectEl) {
    // default aman: jika tidak ada meta, anggap butuh vendor
    if (!selectEl) return true;
    const ctId = selectEl.value;
    if (!ctId) return true;

    const meta = getCostTypeMeta(ctId);
    if (!meta) return true;

    return !!meta.requires_vendor; // 1 => vendor mode, 0 => internal note mode
  }

  function applyCostTypeMode(row, prefix) {
    const ct = row.querySelector(`select[name^="${prefix}-"][name$="-cost_type"]`);
    const vw = row.querySelector(".js-vendor-wrap");
    const nw = row.querySelector(".js-internal-note-wrap");
   
    const vendorMode = vendorModeFromCostType(ct);

    if (vendorMode) {
      vw.classList.remove("d-none");
      nw.classList.add("d-none");

      // optional: kosongkan note saat disembunyikan
      const noteInput = nw.querySelector("input, textarea, select");
      if (noteInput) noteInput.value = "";
    } else {
      vw.classList.add("d-none");
      const vendorSel = vw.querySelector("select");
      if (vendorSel) vendorSel.value = "";

      nw.classList.remove("d-none");
    }
  }

  // ---------- money bind ----------
  function bindMoneyInput(el) {
    if (!el) return;
    if (el.dataset.moneyInit === "1") return;   // cegah double init (penting kalau nanti AJAX replace)
    el.dataset.moneyInit = "1";

    el.addEventListener("focus", () => setTimeout(() => el.select(), 0));
    const format = () => { el.value = fmtID(parseID(el.value)); };
    el.addEventListener("blur", format);
    el.addEventListener("change", format);
    format();
  }

  // ---------- attach row handlers ----------
  function attachRow(row, prefix) {
    const est = row.querySelector(`input[name^="${prefix}-"][name$="-est_amount"]`);
    const act = row.querySelector(`input[name^="${prefix}-"][name$="-actual_amount"]`);

    // format angka
    bindMoneyInput(est);
    bindMoneyInput(act);

    // delete
    const btn = row.querySelector(".remove-row");
    const del = row.querySelector(`input[name^="${prefix}-"][name$="-DELETE"]`);
    if (btn && del && !btn.dataset.delInit) {
      btn.dataset.delInit = "1";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        del.checked = true;
        row.classList.add("d-none");
      });
    }

    // apply vendor/note mode
    applyCostTypeMode(row, prefix);
  }

  // ---------- DOM READY ----------
  document.addEventListener("DOMContentLoaded", function () {
    const prefix = detectPrefix();
    const tbody = document.getElementById("jobcost-body");
    const addBtn = document.getElementById("btn-jobcost-add");
    const tpl = document.getElementById("jobcost-empty-row");

    if (!prefix) {
      console.warn("Formset prefix not found. Pastikan management_form ter-render.");
      return;
    }

    const totalForms = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    if (!tbody || !addBtn || !tpl || !totalForms) return;

    // init existing
    tbody.querySelectorAll("tr.jobcost-row").forEach(row => attachRow(row, prefix));

    // change cost_type => toggle
    tbody.addEventListener("change", function (e) {
      const el = e.target;
      if (!el) return;
      if (el.matches(`select[name^="${prefix}-"][name$="-cost_type"]`)) {
        const row = el.closest(".jobcost-row");
        if (row) applyCostTypeMode(row, prefix);
      }
    });

    // add row (clone from template)
    


    // end add row
  });


})();


(function () {
  "use strict";

  // ---------- helper format angka ID ----------
  function parseID(v) {
    if (!v) return 0;
    let s = String(v).trim();
    if (s.indexOf(",") >= 0) s = s.replace(/\./g, "").replace(",", ".");
    const n = parseFloat(s);
    return isNaN(n) ? 0 : n;
  }

  function fmtID(n) {
    return Number(n || 0).toLocaleString("id-ID", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  // ---------- detect prefix formset ----------
  function detectPrefix() {
    const el = document.querySelector('input[id^="id_"][id$="-TOTAL_FORMS"]');
    if (!el) return null;
    return el.id.replace(/^id_/, "").replace(/-TOTAL_FORMS$/, "");
  }

  // ---------- COST TYPE META (DB-driven) ----------
  function getCostTypeMeta(costTypeId) {
    const map = window.COST_TYPE_META || {};
    return map[String(costTypeId)] || null;
  }

  // ---------- vendor/non-vendor mode ----------
  function vendorModeFromCostType(selectEl) {
    // default aman: jika tidak ada meta, anggap butuh vendor
    if (!selectEl) return true;
    const ctId = selectEl.value;
    if (!ctId) return true;

    const meta = getCostTypeMeta(ctId);
    if (!meta) return true;

    return !!meta.requires_vendor; // 1 => vendor mode, 0 => internal note mode
  }

  function applyCostTypeMode(row, prefix) {
    const ct =
      row.querySelector(`select[name^="${prefix}-"][name$="-cost_type"]`) ||
      row.querySelector('select[name$="-cost_type"]');

    const vw = row.querySelector(".js-vendor-wrap");
    const nw = row.querySelector(".js-internal-note-wrap");
    if (!vw || !nw) return;

    const vendorMode = vendorModeFromCostType(ct);

    if (vendorMode) {
      vw.classList.remove("d-none");
      nw.classList.add("d-none");

      // optional: kosongkan note saat disembunyikan
      const noteInput = nw.querySelector("input, textarea, select");
      if (noteInput) noteInput.value = "";
    } else {
      vw.classList.add("d-none");
      const vendorSel = vw.querySelector("select");
      if (vendorSel) vendorSel.value = "";

      nw.classList.remove("d-none");
    }
  }

  // ---------- money bind ----------
  function bindMoneyInput(el) {
    if (!el) return;
    if (el.dataset.moneyInit === "1") return; // cegah double init
    el.dataset.moneyInit = "1";

    el.addEventListener("focus", () => setTimeout(() => el.select(), 0));
    const format = () => {
      el.value = fmtID(parseID(el.value));
    };
    el.addEventListener("blur", format);
    el.addEventListener("change", format);
    format();
  }

  // ---------- attach row handlers ----------
  function attachRow(row, prefix) {
    const est = row.querySelector(`input[name^="${prefix}-"][name$="-est_amount"]`);
    const act = row.querySelector(`input[name^="${prefix}-"][name$="-actual_amount"]`);

    bindMoneyInput(est);
    bindMoneyInput(act);

    // delete
    const btn = row.querySelector(".remove-row");
    const del = row.querySelector(`input[name^="${prefix}-"][name$="-DELETE"]`);
    if (btn && del && !btn.dataset.delInit) {
      btn.dataset.delInit = "1";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        del.checked = true;
        row.classList.add("d-none");
      });
    }

    applyCostTypeMode(row, prefix);
  }

  // ---------- add new row ----------
  function addNewRow() {

   
    const prefix = detectPrefix();
    const tbody = document.getElementById("jobcost-body");
    const tpl = document.getElementById("jobcost-empty-row");
    const totalForms = prefix ? document.getElementById(`id_${prefix}-TOTAL_FORMS`) : null;

    const touched = document.getElementById("jobcost-touched");
    if (touched) touched.value = "1";  
   
    
    if (!prefix || !tbody || !tpl || !totalForms) return;

    const idx = parseInt(totalForms.value || "0", 10);
    const html = tpl.innerHTML.replace(/__prefix__/g, idx).trim();

    const wrap = document.createElement("tbody");
    wrap.innerHTML = html;
    const row = wrap.querySelector("tr.jobcost-row") || wrap.querySelector("tr");
    if (!row) return;

    tbody.appendChild(row);
    totalForms.value = idx + 1;

    // default angka 0,00 (biar konsisten + trigger required validation kalau >0 dipaksa)
    const est = row.querySelector(`input[name="${prefix}-${idx}-est_amount"]`);
    const act = row.querySelector(`input[name="${prefix}-${idx}-actual_amount"]`);
    if (est) est.value = "0,00";
    if (act) act.value = "0,00";

    // cost_type start kosong (kalau ada empty option)
    const ct = row.querySelector(`select[name="${prefix}-${idx}-cost_type"]`);
    if (ct) ct.value = "";

    attachRow(row, prefix);
  }

  // ======================================================
  // GLOBAL INIT: dipanggil saat load & setelah AJAX replace
  // ======================================================
  window.initJobCostTable = function initJobCostTable() {
    const prefix = detectPrefix();
    if (!prefix) {
      console.warn("Formset prefix not found. Pastikan management_form ter-render.");
      return;
    }

    const tbody = document.getElementById("jobcost-body");
    const tpl = document.getElementById("jobcost-empty-row");
    const totalForms = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    if (!tbody || !tpl || !totalForms) return;

    // init existing rows
    tbody.querySelectorAll("tr.jobcost-row").forEach((row) => attachRow(row, prefix));

    // delegate change cost_type (bind sekali seumur hidup element tbody)
    if (!tbody.dataset.ctDelegateInit) {
      tbody.dataset.ctDelegateInit = "1";
      tbody.addEventListener("change", function (e) {
        const el = e.target;
        if (!el) return;
        if (
          el.matches(`select[name^="${prefix}-"][name$="-cost_type"]`) ||
          el.matches('select[name$="-cost_type"]')
        ) {
          const row = el.closest(".jobcost-row");
          if (row) applyCostTypeMode(row, prefix);
        }
      });
    }

    // NOTE: add button handler tidak di-bind di sini (delegation global), jadi tidak bisa double
  };

  // ======================================================
  // BIND GLOBAL CLICK ONCE (ANTI DOUBLE ADD)
  // ======================================================
  if (!document.body.dataset.jobcostAddBound) {
    document.body.dataset.jobcostAddBound = "1";
    document.addEventListener(
      "click",
      function (e) {
        const btn = e.target.closest("#btn-jobcost-add");
        if (!btn) return;
        e.preventDefault();
        addNewRow();
      },
      true
    );
  }

  // initial load
  document.addEventListener("DOMContentLoaded", function () {
    window.initJobCostTable();
  });
})();
