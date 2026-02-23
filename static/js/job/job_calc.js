(function (window) {

  if (!window.JobUtils) {
    console.error("JobUtils not loaded");
    return;
  }

  const { numID, fmtID } = window.JobUtils;

  function calcDiscountAmount(base, type, value) {
    if (!type || !value) return 0;

    if (type === "AMOUNT") {
      return Math.min(value, base);
    }

    if (type === "PERCENT") {
      return (base * Math.min(value, 100)) / 100;
    }

    return 0;
  }

  function recalc() {

    const qtyEl       = document.getElementById("id_qty");
    const priceEl     = document.getElementById("id_price");
    const discValueEl = document.getElementById("id_discount_value");
    const switchEl    = document.getElementById("discountTypeSwitch");

    const totalEl    = document.getElementById("id_total_amount");
    const taxEl      = document.getElementById("id_tax_amount");
    const grandEl    = document.getElementById("id_grand_total");
    const subtotalEl = document.getElementById("id_subtotal");

    if (!qtyEl || !priceEl) return;

    // =========================
    // BASE (Qty × Price)
    // =========================
    const base = numID(qtyEl.value) * numID(priceEl.value);

    // =========================
    // DISCOUNT
    // =========================
    //const discType  = switchEl && switchEl.checked ? "AMOUNT" : "PERCENT";
    const hiddenTypeEl = document.getElementById("id_discount_type");
    const discType = hiddenTypeEl ? hiddenTypeEl.value : "PERCENT";
   // const discValue = discValueEl ? numID(discValueEl.value) : 0;

    //const discAmount = calcDiscountAmount(base, discType, discValue);
    const discValue = discValueEl ? numID(discValueEl.value) : 0;

    const discAmount = calcDiscountAmount(base, discType, discValue);

    // =========================
    // SUBTOTAL (DPP)
    // =========================
    const subtotal = Math.max(base - discAmount, 0);

    if (subtotalEl) {
      subtotalEl.value = fmtID(subtotal);
    }

    // =========================
    // TAX (PPN only)
    // =========================
    const taxes = window.JobTax
      ? window.JobTax.computeTaxes(subtotal)
      : { vat: 0 };

    const taxAmount = taxes.vat || 0;
    const grand = subtotal + taxAmount;

    // =========================
    // UPDATE DOM
    // =========================
    if (totalEl) totalEl.value = fmtID(base);
    if (taxEl)   taxEl.value   = fmtID(taxAmount);
    if (grandEl) grandEl.value = fmtID(grand);
  }

  // expose only
  window.JobCalc = { recalc };

})(window);