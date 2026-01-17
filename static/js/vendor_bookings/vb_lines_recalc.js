document.addEventListener("DOMContentLoaded", function () {
  window.VBLines = window.VBLines || { plugins: [] };

  function num(v) {
    if (v === null || v === undefined) return 0;
    v = String(v).trim();
    if (!v) return 0;
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

  function recalc(tbody) {
    if (!tbody) return;

    const rows = tbody.querySelectorAll("tr");
    let total = 0;

    rows.forEach((tr) => {
      const del = tr.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (del && del.checked) {
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

  function bindRecalcOnce(getTbody) {
    if (document.body.dataset.vbRecalcBound) return;
    document.body.dataset.vbRecalcBound = "1";

    document.addEventListener("input", function (e) {
      const t = e.target;
      if (!t || !t.name) return;
      if (t.name.endsWith("-qty") || t.name.endsWith("-unit_price")) {
        recalc(getTbody());
      }
    });

    document.addEventListener("change", function (e) {
      const t = e.target;
      if (!t || !t.name) return;
      if (t.name.endsWith("-DELETE")) {
        recalc(getTbody());
      }
    });
  }

  window.VBLines.plugins.push({
    onInit({ tbody }) {
      bindRecalcOnce(() => tbody);
      recalc(tbody);
      // expose optional
      window.VB = window.VB || {};
      window.VB.recalcLines = () => recalc(tbody);
    },
    onRowAdded(tr, { tbody }) {
      recalc(tbody);
    },
  });
});
