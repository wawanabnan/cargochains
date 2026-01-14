//console.log("VB Lines JS loaded");

//document.addEventListener("DOMContentLoaded", function () {
//  console.log("btn-add-line:", document.getElementById("btn-add-line"));
//  console.log("lines-table tbody:", document.querySelector("#lines-table tbody"));
//  console.log("empty-line-row:", document.getElementById("empty-line-row"));
//  console.log("TOTAL_FORMS:", document.querySelector('input[id$="-TOTAL_FORMS"]'));
//});
document.addEventListener("DOMContentLoaded", function () {
  function num(v) {
    if (v === null || v === undefined) return 0;
    v = String(v).trim();
    if (!v) return 0;
    // support id-ID typed number: 1.234,56
    if (v.indexOf(",") >= 0) v = v.replace(/\./g, "").replace(",", ".");
    const n = parseFloat(v);
    return isNaN(n) ? 0 : n;
  }

  function fmt(n) {
    try {
      return Number(n || 0).toLocaleString("id-ID", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    } catch (e) {
      return (n || 0).toFixed(2);
    }
  }

  function detectPrefix() {
    // cari management TOTAL_FORMS
    const el = document.querySelector('input[id$="-TOTAL_FORMS"]');
    if (!el) return null;
    return el.id.replace(/^id_/, "").replace(/-TOTAL_FORMS$/, "");
  }

  const btnAdd = document.getElementById("btn-add-line");
  if (!btnAdd) return;

  const prefix = detectPrefix();
  if (!prefix) {
    console.warn("Formset prefix tidak ditemukan");
    return;
  }

  const totalForms = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  const tbody = document.querySelector("#lines-table tbody");
  const tmpl = document.getElementById("empty-line-row");

  if (!totalForms || !tbody || !tmpl) {
    console.warn("Add Line: element tidak lengkap", { totalForms, tbody, tmpl });
    return;
  }

  function recalc() {
    // hitung dari row yang ada di table
    const rows = tbody.querySelectorAll("tr");
    let total = 0;

    rows.forEach(function (tr) {
      const del = tr.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (del && del.checked) {
        // kalau ada cell subtotal, set 0
        const subEl = tr.querySelector(".vb-subtotal");
        if (subEl) subEl.textContent = fmt(0);
        return;
      }

      const qtyEl = tr.querySelector('input[name$="-qty"]');
      const priceEl = tr.querySelector('input[name$="-unit_price"]');

      const qty = qtyEl ? num(qtyEl.value) : 0;
      const price = priceEl ? num(priceEl.value) : 0;
      const sub = qty * price;

      const subEl = tr.querySelector(".vb-subtotal");
      if (subEl) subEl.textContent = fmt(sub);

      total += sub;
    });

    const totalEl = document.getElementById("vb-total-text");
    if (totalEl) totalEl.textContent = fmt(total);
  }

  function addLine() {
    const idx = parseInt(totalForms.value || "0", 10);
    const html = tmpl.innerHTML.replace(/__prefix__/g, String(idx));
    tbody.insertAdjacentHTML("beforeend", html);
    totalForms.value = String(idx + 1);

    // ✅ HOOK: rebind behaviour untuk row baru (modal/detail/autodesc/select2, dll)
    const newRow = tbody.lastElementChild;
    if (newRow && window.VB && typeof window.VB.rebindRow === "function") {
      try {
        window.VB.rebindRow(newRow);
      } catch (err) {
        console.warn("VB.rebindRow error:", err);
      }
    }

    recalc();
  }

  // events
  btnAdd.addEventListener("click", addLine);

  document.addEventListener("input", function (e) {
    const t = e.target;
    if (!t || !t.name) return;
    if (t.name.endsWith("-qty") || t.name.endsWith("-unit_price")) recalc();
  });

  document.addEventListener("change", function (e) {
    const t = e.target;
    if (!t || !t.name) return;
    if (t.name.endsWith("-DELETE")) recalc();
  });

  // initial calc
  recalc();

  // ✅ HOOK: init behaviour untuk row existing (modal/detail/autodesc/select2, dll)
  if (window.VB && typeof window.VB.init === "function") {
    try {
      window.VB.init();
    } catch (err) {
      console.warn("VB.init error:", err);
    }
  }
});
