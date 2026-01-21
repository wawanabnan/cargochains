(function () {
  function toNum(v) {
    if (v === null || v === undefined) return 0;
    const s = String(v).replace(/,/g, "").trim();
    const n = parseFloat(s);
    return isNaN(n) ? 0 : n;
  }

  function fmt2(n) {
    // simple; kalau mau id-ID bisa pakai Intl.NumberFormat
    return (Math.round((n + Number.EPSILON) * 100) / 100).toFixed(2);
  }

  function getTaxRateFromOption(opt) {
    // option text misal: "VAT 11%"; atau bisa pakai data-rate di option
    const dr = opt.getAttribute("data-rate");
    if (dr !== null && dr !== "") return toNum(dr);

    const m = (opt.textContent || "").match(/(\d+(\.\d+)?)\s*%/);
    return m ? toNum(m[1]) : 0;
  }

  function recalc() {
    const rows = document.querySelectorAll("#vbLinesTable tbody tr.vb-row");
    let subtotal = 0;
    let taxAmount = 0;

    rows.forEach((tr) => {
      const qtyEl = tr.querySelector(".vb-qty");
      const priceEl = tr.querySelector(".vb-unit-price");
      const taxesEl = tr.querySelector(".vb-taxes");
      const amtText = tr.querySelector(".vb-amount-text");

      const qty = toNum(qtyEl ? qtyEl.value : 0);
      const up = toNum(priceEl ? priceEl.value : 0);
      const amount = qty * up;

      subtotal += amount;
      if (amtText) amtText.textContent = fmt2(amount);

      if (taxesEl) {
        const selected = Array.from(taxesEl.selectedOptions || []);
        selected.forEach((opt) => {
          const rate = getTaxRateFromOption(opt) / 100.0;
          taxAmount += amount * rate;
        });
      }
    });

    const discEl = document.getElementById("id_discount_amount");
    const whtEl = document.getElementById("id_wht_rate");
    const discount = toNum(discEl ? discEl.value : 0);
    const whtRate = toNum(whtEl ? whtEl.value : 0) / 100.0;

    const taxableBase = subtotal - discount;
    const whtAmount = taxableBase * whtRate;
    const total = taxableBase + taxAmount - whtAmount;

    const subDom = document.getElementById("vbSubTotal");
    const taxDom = document.getElementById("vbTaxAmount");
    const whtDom = document.getElementById("vbWhtAmount");
    const totDom = document.getElementById("vbTotal");

    if (subDom) subDom.textContent = fmt2(subtotal);
    if (taxDom) taxDom.textContent = fmt2(taxAmount);
    if (whtDom) whtDom.textContent = fmt2(whtAmount);
    if (totDom) totDom.textContent = fmt2(total);
  }

  function bind() {
    document.addEventListener("input", function (e) {
      if (
        e.target.matches(".vb-qty") ||
        e.target.matches(".vb-unit-price") ||
        e.target.matches("#id_discount_amount") ||
        e.target.matches("#id_wht_rate")
      ) recalc();
    });

    document.addEventListener("change", function (e) {
      if (e.target.matches(".vb-taxes")) recalc();
    });

    recalc();
  }

  document.addEventListener("DOMContentLoaded", bind);
})();
