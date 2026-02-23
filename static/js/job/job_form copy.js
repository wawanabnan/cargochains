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

    const kursInput  = document.getElementById("id_kurs_idr");
    const discEl     = document.getElementById("id_discount_value");
    const switchEl   = document.getElementById("discountTypeSwitch");
     const hiddenInput = document.getElementById("id_discount_type");
    const label = document.getElementById("discountTypeLabel");

    if (!switchEl || !hiddenInput) return;

    // ===== SET INITIAL FROM DJANGO VALUE =====
    const initialType = hiddenInput.value || "PERCENT";

    if (initialType === "AMOUNT") {
        switchEl.checked = true;
        label.lastChild.textContent = " Discount (Rp)";
    } else {
        switchEl.checked = false;
        label.lastChild.textContent = " Discount (%)";
        hiddenInput.value = "PERCENT";
    }

    // ===== UPDATE WHEN TOGGLED =====
    discEl.addEventListener("blur", function () {

      let val = numID(discEl.value);

      if (!switchEl.checked && val > 100) {
        val = 100;
      }

      if (val < 0) val = 0;

      discEl.value = fmtID(val);

      window.JobCalc?.recalc();
    });


    const dpEl = document.getElementById("id_down_payment_percent");
    const dpAmountDisplay = document.getElementById("id_down_payment_amount_display");

    const taxesEl = document.getElementById("id_taxes");

    // =========================
    // READONLY CALCULATED FIELDS
    // =========================
    [totalEl, taxEl, pphEl, grandEl].forEach(setReadonly);

    // =========================
    // DISCOUNT MODE TRACKING
    // =========================
    let discountMode = "PERCENT";

    if (switchEl) {
      discountMode = switchEl.checked ? "AMOUNT" : "PERCENT";
      switchEl.addEventListener("change", function () {
        discountMode = switchEl.checked ? "AMOUNT" : "PERCENT";
        if (window.JobCalc) window.JobCalc.recalc();
      });
    }

    // =========================
    // FORMAT QTY & PRICE
    // =========================
    [qtyEl, priceEl].forEach(function (el) {
      if (!el) return;

      el.addEventListener("focus", function () {
        setTimeout(() => el.select(), 0);
      });

      el.addEventListener("blur", function () {
        el.value = fmtID(numID(el.value));
        if (window.JobCalc) window.JobCalc.recalc();
      });
    });

    // =========================
    // DISCOUNT FIELD
    // =========================
    if (discEl) {
      discEl.addEventListener("focus", function () {
        setTimeout(() => discEl.select(), 0);
      });

      discEl.addEventListener("blur", function () {

        let val = numID(discEl.value);

        if (discountMode === "PERCENT" && val > 100) {
          val = 100;
        }

        discEl.value = fmtID(val);

        if (window.JobCalc) window.JobCalc.recalc();
      });
    }

    // =========================
    // DOWN PAYMENT (%)
    // =========================
    if (dpEl) {

      dpEl.addEventListener("focus", function () {
        setTimeout(() => dpEl.select(), 0);
      });

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

    // =========================
    // 🔥 BIND RECALC EVENTS (FIX UTAMA)
    // =========================
    if (qtyEl) {
      qtyEl.addEventListener("input", () => window.JobCalc?.recalc());
    }

    if (priceEl) {
      priceEl.addEventListener("input", () => window.JobCalc?.recalc());
    }

    if (taxesEl) {
      taxesEl.addEventListener("change", () => window.JobCalc?.recalc());
    }

    if (discEl) {
      discEl.addEventListener("input", () => window.JobCalc?.recalc());
    }

    // 🔥 WAJIB: jalankan sekali saat halaman load (edit page fix)
    // 🔥 FORMAT DP SAAT LOAD (EDIT PAGE FIX)
    if (dpEl && dpEl.value) {
      dpEl.value = fmtID(numID(dpEl.value));
    }

    // jalankan kalkulasi awal
    if (window.JobCalc) {
      window.JobCalc.recalc();
    }

updateDownPaymentAmount();

    // =========================
    // SUBMIT NORMALIZE
    // =========================
    form.addEventListener("submit", function () {
 
      if (switchEl && hiddenInput && discEl) {

        // ===== DEFAULT RENDER =====
        switchEl.checked = false; // default PERCENT
        hiddenInput.value = "PERCENT";
        label.textContent = "Discount (%)";
        discEl.value = "0,00";

        // ===== SAAT SWITCH DIUBAH =====
        switchEl.addEventListener("change", function () {

          if (switchEl.checked) {
            // MODE AMOUNT
            hiddenInput.value = "AMOUNT";
            label.textContent = "Discount (Rp)";
            discEl.value = "0,00";

            setTimeout(() => discEl.focus(), 0);

          } else {
            // MODE PERCENT
            hiddenInput.value = "PERCENT";
            label.textContent = "Discount (%)";
            discEl.value = "0,00";
          }

          window.JobCalc?.recalc();
        });

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

    // =========================
    // FLATPICKR
    // =========================
    if (typeof flatpickr !== "undefined") {
      document.querySelectorAll(".js-jobdate").forEach(function (el) {
        const fp = flatpickr(el, {
          dateFormat: "d-m-Y",
          allowInput: true,
          clickOpens: true,
          altInput: false,
          defaultDate: el.value || null,
          locale: { firstDayOfWeek: 1 }
        });

        el.addEventListener("focus", function () {
          fp.open();
        });
      });
    }

  });

})(window);