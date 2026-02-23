(function (window) {

  document.addEventListener("DOMContentLoaded", function () {

    const { numID, fmtID } = window.JobUtils;

    const discTypeEl = document.getElementById("id_discount_type");
    const discValueEl = document.getElementById("id_discount_value");
    const saveDiscountBtn = document.getElementById("saveDiscountBtn");
    const discountDisplay = document.getElementById("discount_display");
    const discountModalEl = document.getElementById("discountModal");

    if (!discTypeEl || !discValueEl) return;

    // =========================
    // TYPE CHANGE
    // =========================
    discTypeEl.addEventListener("change", function () {

      if (discTypeEl.value === "PERCENT") {
        discValueEl.value = "0";
      } else if (discTypeEl.value === "AMOUNT") {
        discValueEl.value = "0";
      }

      setTimeout(() => {
        discValueEl.focus();
        discValueEl.select();
      }, 50);
    });



    // =========================
// SANITIZE DISCOUNT INPUT
// =========================
discValueEl.addEventListener("input", function () {

  let val = discValueEl.value;

  // hanya izinkan digit, titik dan koma
  val = val.replace(/[^\d.,]/g, "");

  // hanya boleh satu koma (desimal)
  const parts = val.split(",");
  if (parts.length > 2) {
    val = parts[0] + "," + parts.slice(1).join("");
  }

  discValueEl.value = val;

});

    // =========================
    // BLUR VALIDATION (FINAL FIX)
    // =========================
    discValueEl.addEventListener("blur", function () {

    let value = numID(discValueEl.value);

    // tidak boleh negatif
    if (value < 0) value = 0;

    // TIDAK ada lagi limit percent di sini
    // limit percent sudah aman di calcDiscountAmount()

    discValueEl.value = fmtID(value);

    if (window.JobCalc) {
        window.JobCalc.recalc();
    }

    });

    // =========================
    // APPLY BUTTON
    // =========================
    if (saveDiscountBtn) {
      saveDiscountBtn.addEventListener("click", function () {

        const type = discTypeEl.value;
        let value = numID(discValueEl.value);

        if (type === "PERCENT") {
          if (value < 0) value = 0;
          if (value > 100) value = 100;

          discValueEl.value = value; // RAW
          discountDisplay.value = value + " %";
        }

        if (type === "AMOUNT") {
          if (value < 0) value = 0;

          discValueEl.value = value; // RAW
          discountDisplay.value = fmtID(value);
        }

        if (window.JobCalc && typeof window.JobCalc.recalc === "function") {
          window.JobCalc.recalc();
        }

        if (discountModalEl) {
          const modal = bootstrap.Modal.getInstance(discountModalEl);
          if (modal) modal.hide();
        }

      });
    }

    const switchEl = document.getElementById("discountTypeSwitch");
    const labelEl  = document.getElementById("discountTypeLabel");
    const discValEl = document.getElementById("id_discount_value");

    if (!switchEl || !labelEl) return;

    function updateDiscountLabel() {
        if (switchEl.checked) {
            labelEl.textContent = "Discount Amount";
             // pindahkan kursor ke subtotal
            if (discValEl) {
                discValEl.focus();
                discValEl.select?.(); // optional: blok angkanya
            }

        } else {
            labelEl.textContent = "Discount (%)";
        }
    }

    switchEl.addEventListener("change", function () {
        updateDiscountLabel();

        // kalau mau langsung hitung ulang:
        if (window.JobCalc) {
            window.JobCalc.recalc();
        }
    });


    
    // set default saat load
    updateDiscountLabel();


  });
})(window);