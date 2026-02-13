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
    const num = Number(n || 0);
    if (!isFinite(num)) return "0,00";

    const fixed = num.toFixed(2);
    let [intPart, decPart] = fixed.split(".");
    intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return `${intPart},${decPart}`;
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

  function pick(row, prefix, suffix) {
    return (
      row.querySelector(`input[name^="${prefix}-"][name$="-${suffix}"]`) ||
      row.querySelector(`select[name^="${prefix}-"][name$="-${suffix}"]`) ||
      row.querySelector(`input[name$="-${suffix}"]`) ||
      row.querySelector(`select[name$="-${suffix}"]`)
    );
  }

  // ---------- COST TYPE META (DB-driven) ----------
  function getCostTypeMeta(costTypeId) {
    const map = window.COST_TYPE_META || {};
    return map[String(costTypeId)] || null;
  }

  function vendorModeFromCostType(selectEl) {
    if (!selectEl) return true;

    // 1) prioritas data-requires-vendor dari option
    const opt =
      selectEl.options && selectEl.selectedIndex >= 0
        ? selectEl.options[selectEl.selectedIndex]
        : null;

    const attr = opt ? opt.getAttribute("data-requires-vendor") : null;
    if (attr === "1") return true;
    if (attr === "0") return false;

    // 2) fallback meta map
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

    // paksa tampil kalau invalid (biar merah keliatan)
    const vEl = row.querySelector('select[name$="-vendor"]');
    const nEl = row.querySelector(
      'input[name$="-internal_note"], textarea[name$="-internal_note"]'
    );
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

  function bindQtyInput(el) {
    if (!el || el.dataset.qtyInit) return;
    el.dataset.qtyInit = "1";
    el.addEventListener("blur", function () {
      const n = parseID(el.value);
      el.value = fmtID(n);
    });
  }

  // ---------- Calc amount & total ----------
  function calcAmount(row, prefix) {
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

    if (amount > 0) estEl.classList.remove("is-invalid");

    updateEstimatedTotal();
  }

  function updateEstimatedTotal() {
    const out = document.getElementById("jobcost-est-total");
    if (!out) return;

    let total = 0;

    document.querySelectorAll("#jobcost-body tr.jobcost-row").forEach((row) => {
      // skip deleted/hidden
      const del = row.querySelector('input[name$="-DELETE"]');
      if (del && del.checked) return;
      if (row.classList.contains("d-none")) return;

      const est = row.querySelector('input[name$="-est_amount"]');
      total += parseID(est ? est.value : 0);
    });

    out.textContent = fmtID(total);
  }

  // ---------- Expand/Collapse Detail Row ----------
  function getDetailRow(mainRow) {
    const next = mainRow ? mainRow.nextElementSibling : null;
    if (next && next.classList && next.classList.contains("jobcost-detail-row")) return next;
    return null;
  }

  function refreshCostDetail(mainRow) {
    const detailRow = getDetailRow(mainRow);
    if (!detailRow) return;

    // qty (ambil dari input agar realtime)
    let qty = 0;
    const qtyInput = mainRow.querySelector('input[name$="-qty"]');
    if (qtyInput) qty = Number(parseID(qtyInput.value || "0"));
    else qty = Number(mainRow.dataset.qty || 0);

    const allocated = Number(mainRow.dataset.allocated || 0);
    const remaining = Math.max(qty - allocated, 0);

    const elAlloc = detailRow.querySelector(".js-alloc-qty");
    const elRem = detailRow.querySelector(".js-rem-qty");
    const badge = detailRow.querySelector(".js-so-badge");
    const btnSO = detailRow.querySelector(".js-create-so");
    // =====================
    // Amount to SO (qty x price)
    // =====================
    const priceInput = mainRow.querySelector('input[name$="-price"]');
    const curSelect  = mainRow.querySelector('select[name$="-currency"]');

    const price = priceInput ? Number(parseID(priceInput.value || "0")) : 0;
    const ccyText = curSelect ? (curSelect.options[curSelect.selectedIndex]?.text || "") : "";

    const soAmount = qty * price; // selalu original currency

    const elSoAmt = detailRow.querySelector(".js-so-amt");
    const elSoCcy = detailRow.querySelector(".js-so-ccy");

    if (elSoAmt) elSoAmt.textContent = fmtID(soAmount);
    if (elSoCcy) elSoCcy.textContent = ccyText || "";



    if (elAlloc) elAlloc.textContent = fmtID(allocated);
    if (elRem) elRem.textContent = fmtID(remaining);

    if (elAlloc) {
      elAlloc.textContent = fmtID(allocated);

      elAlloc.classList.remove("text-success","text-primary","text-muted");

      if (allocated <= 0) {
        elAlloc.classList.add("text-muted");
      } else if (remaining <= 0) {
        elAlloc.classList.add("text-success");
      } else {
        elAlloc.classList.add("text-primary");
      }
    }

    if (badge) {
      if (qty > 0 && remaining <= 0) {
        badge.className = "badge text-bg-success js-so-badge";
        badge.textContent = "Fully SO";
      } else if (allocated > 0 && remaining > 0) {
        badge.className = "badge text-bg-warning js-so-badge";
        badge.textContent = "Partial";
      } else {
        badge.className = "badge text-bg-secondary js-so-badge";
        badge.textContent = "Not SO";
      }
    }

    if (btnSO) btnSO.classList.toggle("d-none", !(remaining > 0));

    // cache
    mainRow.dataset.qty = String(qty);
  }

  function bindCostExpandCollapse(container) {
    if (!container) return;
    if (container.dataset.costExpandBound === "1") return; // anti double bind
    container.dataset.costExpandBound = "1";

    container.addEventListener("click", function (e) {
      const btn = e.target.closest(".js-toggle-cost-detail");
      if (!btn) return;

      const mainRow = btn.closest("tr.jobcost-row");
      if (!mainRow) return;

      const detailRow = getDetailRow(mainRow);
      if (!detailRow) return;

      refreshCostDetail(mainRow);

      const opening = detailRow.classList.contains("d-none");
      detailRow.classList.toggle("d-none", !opening);

      btn.setAttribute("aria-expanded", opening ? "true" : "false");
      const chev = btn.querySelector(".js-chevron");
      if (chev) chev.textContent = opening ? "▼" : "▶";
    });

    container.addEventListener("input", function (e) {
      const qtyInput = e.target.closest('input[name$="-qty"]');
      if (!qtyInput) return;

      const mainRow = qtyInput.closest("tr.jobcost-row");
      if (!mainRow) return;

      const detailRow = getDetailRow(mainRow);
      if (!detailRow || detailRow.classList.contains("d-none")) return;

      refreshCostDetail(mainRow);
    });
  }

  // ---------- Readonly lock ----------
  function applyCostReadonly() {
  const wrap = document.getElementById("jobcost-area");
  if (!wrap) return;

  const locked = wrap.dataset.costLocked === "1";

  // disable hanya field input
  wrap.querySelectorAll("input, select, textarea").forEach(el => {
    el.disabled = locked;
  });

  // tombol expand tetap aktif
  wrap.querySelectorAll(".js-toggle-cost-detail").forEach(btn => {
    btn.disabled = false;
  });
}

  // ---------- ATTACH ROW ----------
  function attachRow(row, prefix) {
    const qtyEl = row.querySelector('input[name$="-qty"]');
    const priceEl = row.querySelector('input[name$="-price"]');
    const rateEl = row.querySelector('input[name$="-rate"]');
    const curEl = row.querySelector('select[name$="-currency"]');

    const estEl = row.querySelector('input[name$="-est_amount"]');
    const actEl = row.querySelector('input[name$="-actual_amount"]');

    bindQtyInput(qtyEl);
    bindMoneyInput(priceEl);
    bindMoneyInput(rateEl);
    bindMoneyInput(estEl);
    bindMoneyInput(actEl);

    // realtime calc
    [qtyEl, priceEl, rateEl].forEach((el) => {
      if (!el || el.dataset.calcInit) return;
      el.dataset.calcInit = "1";

      el.addEventListener("input", function () {
        markTouched();
        calcAmount(row, prefix);
      });
    });

    // currency -> auto rate
    if (curEl && rateEl && !curEl.dataset.rateInit) {
      curEl.dataset.rateInit = "1";

      curEl.addEventListener("change", async function () {
        const currencyId = curEl.value;
        if (!currencyId) return;

        const url = `/api/exchange-rate/latest/?currency_id=${encodeURIComponent(currencyId)}`;

        try {
          const res = await fetch(url, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
            credentials: "same-origin",
          });
          if (!res.ok) return;

          const data = await res.json();
          if (!data.ok || !data.rate_to_idr) return;

          rateEl.value = fmtID(parseFloat(data.rate_to_idr));

          markTouched();
          calcAmount(row, prefix);
          updateEstimatedTotal();
        } catch (e) {
          // silent
        }
      });
    }

    // initial
    calcAmount(row, prefix);
    updateEstimatedTotal();
  }

  // ---------- REMOVE row (main + detail) ----------
  function hideRowWithDetail(mainRow) {
    const detail = getDetailRow(mainRow);
    if (detail) detail.classList.add("d-none");
    mainRow.classList.add("d-none");
  }

  function removeRowWithDetail(mainRow) {
    const detail = getDetailRow(mainRow);
    if (detail) detail.remove();
    mainRow.remove();
  }

  // ---------- ADD NEW ROW (append main + detail) ----------
  function addNewRow() {
    const prefix = detectPrefix();
    const tbody = document.getElementById("jobcost-body");
    const tpl = document.getElementById("jobcost-empty-row");
    const totalForms = prefix ? document.getElementById(`id_${prefix}-TOTAL_FORMS`) : null;
    if (!prefix || !tbody || !tpl || !totalForms) return;

    markTouched();

    const idx = parseInt(totalForms.value || "0", 10);
    const html = tpl.innerHTML.replace(/__prefix__/g, idx).trim();

    const wrap = document.createElement("tbody");
    wrap.innerHTML = html;

    const rows = wrap.querySelectorAll("tr");
    if (!rows || rows.length === 0) return;

    // append ALL rows (main + detail)
    rows.forEach((r) => tbody.appendChild(r));
    const row = rows[0]; // main row

    totalForms.value = idx + 1;

    // default values
    const est = row.querySelector(`input[name="${prefix}-${idx}-est_amount"]`);
    const act = row.querySelector(`input[name="${prefix}-${idx}-actual_amount"]`);
    if (est) est.value = "0,00";
    if (act) act.value = "0,00";

    const ct = row.querySelector(`select[name="${prefix}-${idx}-cost_type"]`);
    if (ct) ct.value = "";

    const qty = row.querySelector(`input[name="${prefix}-${idx}-qty"]`);
    const price = row.querySelector(`input[name="${prefix}-${idx}-price"]`);
    const rate = row.querySelector(`input[name="${prefix}-${idx}-rate"]`);

    if (qty) qty.value = "1,00";
    if (price) price.value = "0,00";
    if (rate) rate.value = "1,00";

    attachRow(row, prefix);
    applyCostTypeMode(row, prefix);

    // refresh detail row content if user opens it
    row.dataset.qty = "1";
    row.dataset.allocated = row.dataset.allocated || "0";

    applyCostReadonly();
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

    // init existing main rows
    tbody.querySelectorAll("tr.jobcost-row").forEach((row) => {
      attachRow(row, prefix);
      applyCostTypeMode(row, prefix);
    });

    // delegate change cost_type (bind sekali)
    if (!tbody.dataset.ctDelegateInit) {
      tbody.dataset.ctDelegateInit = "1";
      tbody.addEventListener("change", function (e) {
        const el = e.target;
        if (!el) return;

        if (
          el.matches(`select[name^="${prefix}-"][name$="-cost_type"]`) ||
          el.matches('select[name$="-cost_type"]')
        ) {
          const row = el.closest("tr.jobcost-row");
          if (row) applyCostTypeMode(row, prefix);
        }
      });
    }

    // bind expand/collapse once (AJAX safe)
    const area = document.getElementById("jobcost-area") || document;
    bindCostExpandCollapse(area);

    // bind remove once via delegation (AJAX safe)
    if (!tbody.dataset.removeDelegateInit) {
      tbody.dataset.removeDelegateInit = "1";
      tbody.addEventListener("click", function (e) {
        const btn = e.target.closest(".remove-row");
        if (!btn) return;

        e.preventDefault();
        markTouched();

        const mainRow = btn.closest("tr.jobcost-row");
        if (!mainRow) return;

        const del = mainRow.querySelector('input[name$="-DELETE"]');

        if (del) {
          // existing row -> mark DELETE & hide both
          del.checked = true;
          hideRowWithDetail(mainRow);
          updateEstimatedTotal();
          return;
        }

        // new row (no DELETE checkbox) -> remove DOM rows
        removeRowWithDetail(mainRow);
        updateEstimatedTotal();
      });
    }

    applyCostReadonly();
    updateEstimatedTotal();
  };

  // ======================================================
  // BIND ADD BUTTON ONCE
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
