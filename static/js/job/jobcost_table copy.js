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

  function pick(row, prefix, suffix) {
    return (
      row.querySelector(`input[name^="${prefix}-"][name$="-${suffix}"]`) ||
      row.querySelector(`input[name$="-${suffix}"]`)
    );
  }

  function calcAmount2(row, prefix) {
    const qtyEl = pick(row, prefix, "qty");
    const priceEl = pick(row, prefix, "price");
    const rateEl = pick(row, prefix, "rate");
    const estEl = pick(row, prefix, "est_amount");

    if (!qtyEl || !priceEl || !rateEl || !estEl) return;

    const qty = parseID(qtyEl.value);
    const price = parseID(priceEl.value);
    const rate = parseID(rateEl.value) || 1;

    const amount = qty * price * rate;


    estEl.value = fmtID(amount);
    estEl.dispatchEvent(new Event("change", { bubbles: true }));
    if (estEl) {
      estEl.value = fmtID(amount);

      // ✅ bersihkan merah kalau sudah valid
      if (amount > 0) estEl.classList.remove("is-invalid");
    }

  }

  function calcAmount(row) {
    const qtyEl   = row.querySelector('input[name$="-qty"]');
    const priceEl = row.querySelector('input[name$="-price"]');
    const rateEl  = row.querySelector('input[name$="-rate"]');
    const estEl   = row.querySelector('input[name$="-est_amount"]');

    if (!qtyEl || !priceEl || !rateEl || !estEl) return;

    const qty   = parseID(qtyEl.value);      // aman untuk "1.00" dan "1,00"
    const price = parseID(priceEl.value);    // "10.000,00"
    const rate  = parseID(rateEl.value);     // "1,00"

    const amount = qty * price * rate;
    estEl.value = fmtID(amount);

    // bersihkan merah kalau sudah valid
    if (amount > 0) estEl.classList.remove("is-invalid");

    updateEstimatedTotal();  // <--- penting
  }




  function fmtID(n) {
    return Number(n || 0).toLocaleString("id-ID", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }


  

  function detectPrefix() {
    const el = document.querySelector('input[id^="id_"][id$="-TOTAL_FORMS"]');
    if (!el) return null;
    return el.id.replace(/^id_/, "").replace(/-TOTAL_FORMS$/, "");
  }

  function markTouched() {
    const touched = document.getElementById("jobcost-touched");
    if (touched) touched.value = "1";
  }

  // ---------- COST TYPE META (DB-driven) ----------
  function getCostTypeMeta(costTypeId) {
    const map = window.COST_TYPE_META || {};
    return map[String(costTypeId)] || null;
  }

  function vendorModeFromCostType(selectEl) {
    // default aman: jika tidak ada meta, anggap butuh vendor
    if (!selectEl) return true;
    const ctId = selectEl.value;
    if (!ctId) return true;

    const meta = getCostTypeMeta(ctId);
    if (!meta) return true;

    return !!meta.requires_vendor; // true => vendor mode, false => internal note mode
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

    // ✅ OVERRIDE: kalau field invalid, paksa tampil biar merah kelihatan
    const vEl = row.querySelector('select[name$="-vendor"]');
    const nEl = row.querySelector('input[name$="-internal_note"], textarea[name$="-internal_note"]');

    if (vEl && vEl.classList.contains("is-invalid")) vw.classList.remove("d-none");
    if (nEl && nEl.classList.contains("is-invalid")) nw.classList.remove("d-none");
  }

  // ---------- money bind ----------
  function bindMoneyInput(el) {
    if (!el) return;
    if (el.type === "hidden" || el.disabled) return;
    if (el.dataset.moneyInit === "1") return;
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

    const qty = row.querySelector('input[name$="-qty"]');
    bindQtyInput(qty);

    // delete (soft delete via formset DELETE)
    const btn = row.querySelector(".remove-row");
    const del = row.querySelector(`input[name^="${prefix}-"][name$="-DELETE"]`);

    if (btn && del && !btn.dataset.delInit) {
      btn.dataset.delInit = "1";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        markTouched(); // ✅ delete dianggap perubahan
        del.checked = true;
        row.classList.add("d-none");
      });

      const estEl = row.querySelector(`input[name^="${prefix}-"][name$="-est_amount"]`) || row.querySelector(`input[name$="-est_amount"]`);
      if (estEl && parseID(estEl.value) > 0) {
        estEl.classList.remove("is-invalid");
      }
      

    }


    //Exchange Rate
    


    // ===== qty / price / rate (suffix-based, no double const) =====
    const qtyEl   = row.querySelector('input[name$="-qty"]');
    const priceEl = row.querySelector('input[name$="-price"]');
    const rateEl  = row.querySelector('input[name$="-rate"]');

    bindQtyInput(qtyEl);
    bindMoneyInput(priceEl);
    bindMoneyInput(rateEl);

    // realtime calc + mark touched
    [qtyEl, priceEl, rateEl].forEach((el) => {
      if (!el || el.dataset.calcInit) return;
      el.dataset.calcInit = "1";

      el.addEventListener("input", function () {
        markTouched();
        calcAmount(row); // <-- pakai versi calcAmount tanpa prefix
      });
    });

    // initial calc
    calcAmount(row);


    applyCostTypeMode(row, prefix);

    // change apa pun di row -> touched (buat edit existing)
    if (!row.dataset.touchInit) {
      row.dataset.touchInit = "1";
      row.addEventListener("change", markTouched, true);
      row.addEventListener("input", markTouched, true);
    }
  }

  function addNewRow() {
    const prefix = detectPrefix();
    const tbody = document.getElementById("jobcost-body");
    const tpl = document.getElementById("jobcost-empty-row");
    const totalForms = prefix ? document.getElementById(`id_${prefix}-TOTAL_FORMS`) : null;
    if (!prefix || !tbody || !tpl || !totalForms) return;

    markTouched(); // ✅ add row dianggap perubahan

    const idx = parseInt(totalForms.value || "0", 10);
    const html = tpl.innerHTML.replace(/__prefix__/g, idx).trim();

    const wrap = document.createElement("tbody");
    wrap.innerHTML = html;
    const row = wrap.querySelector("tr.jobcost-row") || wrap.querySelector("tr");
    if (!row) return;

    tbody.appendChild(row);
    totalForms.value = idx + 1;

    // ✅ IMPORTANT:
    // Paksa numeric default "0,00" agar Django menganggap form "changed"
    // sehingga saat SAVE tanpa isi, formset tetap divalidasi dan row tidak hilang.
    const est = row.querySelector(`input[name="${prefix}-${idx}-est_amount"]`);
    const act = row.querySelector(`input[name="${prefix}-${idx}-actual_amount"]`);
    if (est) est.value = "0,00";
    if (act) act.value = "0,00";

    const ct = row.querySelector(`select[name="${prefix}-${idx}-cost_type"]`);
    if (ct) ct.value = "";

    // ✅ default baru: qty=1,00 price=0,00 rate=1,00
    const qty = row.querySelector(`input[name="${prefix}-${idx}-qty"]`);
    const price = row.querySelector(`input[name="${prefix}-${idx}-price"]`);
    const rate = row.querySelector(`input[name="${prefix}-${idx}-rate"]`);

    if (qty) qty.value = "1.00";        // input type=number -> pakai dot
    if (price) price.value = "0,00";    // money input -> format ID
    if (rate) rate.value = "1,00";      // money input -> format ID


    attachRow(row, prefix);
    calcAmount(row, prefix);

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

    // delegate change cost_type (bind sekali per tbody element)
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
  };

  // ======================================================
  // BIND ADD BUTTON ONCE (delegation)
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

  function bindQtyInput(el) {
    if (!el || el.dataset.qtyInit) return;
    el.dataset.qtyInit = "1";

    el.addEventListener("blur", function () {
      const n = parseID(el.value);
      el.value = fmtID(n);          // hasil: "2,00"
    });
  }


  function updateEstimatedTotal(prefix) {
    const out = document.getElementById("jobcost-est-total");
    if (!out) return;

    let total = 0;

    document.querySelectorAll("#jobcost-body tr.jobcost-row").forEach((row) => {
      const del = row.querySelector('input[name$="-DELETE"]');
      if (del && del.checked) return;

      const est = row.querySelector(`input[name^="${prefix}-"][name$="-est_amount"]`)
              || row.querySelector('input[name$="-est_amount"]');

      total += parseID(est ? est.value : 0);
    });

    out.textContent = fmtID(total);
  }

  // initial load
  document.addEventListener("DOMContentLoaded", function () {
    window.initJobCostTable();
  });
})();
