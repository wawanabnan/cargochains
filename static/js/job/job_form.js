(function (window) {

  const { numID, fmtID } = window.JobUtils;

  function setReadonly(el) {
    if (!el) return;
    el.readOnly = true;
    el.setAttribute("tabindex", "-1");
  }

  function normalizeKursRaw(v) {
    let s = String(v ?? "").trim().replace(/\s+/g, "");
    if (!s) return "";
    if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
    s = s.replace(/[^\d.]/g, "");
    const parts = s.split(".");
    const intPart = parts[0] || "";
    const decPart = (parts[1] || "").slice(0, 3);
    return decPart ? `${intPart}.${decPart}` : intPart;
  }

  document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("jobOrderForm");
    if (!form) return;

    const qtyEl   = document.getElementById("id_qty");
    const priceEl = document.getElementById("id_price");
    const totalEl = document.getElementById("id_total_amount");
    const taxEl   = document.getElementById("id_tax_amount");
    const pphEl   = document.getElementById("id_pph_amount");
    const grandEl = document.getElementById("id_grand_total");

    const discEl   = document.getElementById("id_discount_value");
    const switchEl = document.getElementById("discountTypeSwitch");
    const hiddenInput = document.getElementById("id_discount_type");
    const label = document.getElementById("discountTypeLabel");

    const dpEl = document.getElementById("id_down_payment_percent");
    const dpAmountDisplay = document.getElementById("id_down_payment_amount_display");
    const taxesEl = document.getElementById("id_taxes");
    const kursInput = document.getElementById("id_kurs_idr");

    // =========================
    // READONLY
    // =========================
    [totalEl, taxEl, pphEl, grandEl].forEach(setReadonly);

    // =========================
    // DISCOUNT (EDIT SAFE)
    // =========================
    if (switchEl && hiddenInput && discEl) {

      // Ambil dari server (EDIT SAFE)
      const currentType = hiddenInput.value || "PERCENT";
      switchEl.checked = currentType === "AMOUNT";

      if (label) {
        label.textContent = switchEl.checked
          ? "Discount (Rp)"
          : "Discount (%)";
      }

      if (discEl.value) {
        discEl.value = fmtID(numID(discEl.value));
      }
      switchEl.addEventListener("change", function () {

        hiddenInput.value = switchEl.checked ? "AMOUNT" : "PERCENT";

        if (label) {
          label.textContent = switchEl.checked
            ? "Discount (Rp)"
            : "Discount (%)";
        }

        discEl.value = "0,00";
        setTimeout(() => {
          discEl.focus();
          discEl.select();
        }, 0);

        window.JobCalc?.recalc();
      });

      discEl.addEventListener("blur", function () {

        let val = numID(discEl.value);

        if (!switchEl.checked && val > 100) {
          val = 100;
        }

        if (val < 0) val = 0;

        discEl.value = fmtID(val);
        window.JobCalc?.recalc();
      });
    }

    // =========================
    // QTY & PRICE
    // =========================
    [qtyEl, priceEl].forEach(function (el) {
      if (!el) return;

      el.addEventListener("focus", () => setTimeout(() => el.select(), 0));

      el.addEventListener("blur", function () {
        el.value = fmtID(numID(el.value));
        window.JobCalc?.recalc();
      });

      el.addEventListener("input", () => window.JobCalc?.recalc());
    });

    if (discEl) {
      discEl.addEventListener("input", () => window.JobCalc?.recalc());
    }

    if (taxesEl) {
      taxesEl.addEventListener("change", () => window.JobCalc?.recalc());
    }

    // =========================
    // DOWN PAYMENT
    // =========================
    if (dpEl) {

      dpEl.addEventListener("focus", () => setTimeout(() => dpEl.select(), 0));

      dpEl.addEventListener("blur", function () {

        let val = numID(dpEl.value);

        if (val < 0) val = 0;
        if (val > 100) val = 100;

        dpEl.value = fmtID(val);
        updateDownPaymentAmount();
      });
    }

    function updateDownPaymentAmount() {
      if (!dpEl || !grandEl || !dpAmountDisplay) return;
      const dpPercent = numID(dpEl.value);
      const grandTotal = numID(grandEl.value);
      const dpAmount = (dpPercent / 100) * grandTotal;
      dpAmountDisplay.value = fmtID(dpAmount);
    }

    // ❌ TIDAK ADA recalc saat load
    // ❌ TIDAK ADA reset discount saat load

    updateDownPaymentAmount();

    // =========================
    // SUBMIT
    // =========================
    form.addEventListener("submit", function () {

      if (switchEl && hiddenInput) {
        hiddenInput.value = switchEl.checked ? "AMOUNT" : "PERCENT";
      }

      if (qtyEl) qtyEl.value = numID(qtyEl.value);
      if (priceEl) priceEl.value = numID(priceEl.value);
      if (discEl) discEl.value = numID(discEl.value);
      if (dpEl) dpEl.value = numID(dpEl.value);

      if (totalEl) totalEl.value = numID(totalEl.value);
      if (taxEl) taxEl.value = numID(taxEl.value);
      if (pphEl) pphEl.value = numID(pphEl.value);
      if (grandEl) grandEl.value = numID(grandEl.value);

      if (kursInput) {
        kursInput.value =
          kursInput.dataset.raw ||
          normalizeKursRaw(kursInput.value) ||
          "";
      }
    });

    if (discEl && totalEl) {

      const base = numID(totalEl.value);
      const discountVal = numID(discEl.value);
      const isPercent = !switchEl.checked;

      let discountAmount = 0;

      if (isPercent) {
        discountAmount = base * discountVal / 100;
      } else {
        discountAmount = discountVal;
      }

      const subtotal = base - discountAmount;

      const subtotalEl = document.getElementById("id_subtotal");
      if (subtotalEl) {
        subtotalEl.value = fmtID(subtotal);
      }
    }
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
    const discType  = switchEl && switchEl.checked ? "AMOUNT" : "PERCENT";
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

  });

})(window);