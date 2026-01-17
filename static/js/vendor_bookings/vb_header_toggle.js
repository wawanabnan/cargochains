(function () {
  const BASIC = "BASIC";
  const SPEC = ["SEA", "AIR", "INLAND"];

  function show(selector, yes) {
    document.querySelectorAll(selector).forEach((el) => {
      el.classList.toggle("d-none", !yes);
    });
  }

  function toggleByBookingGroup() {
    const el = document.getElementById("id_booking_group") || document.querySelector('[name="booking_group"]');
    if (!el) return;

    const group = String(el.value || "").trim();

    // BASIC always visible
    show('[data-booking-section="BASIC"]', true);

    // hide all specific sections first
    SPEC.forEach((k) => show(`[data-booking-section="${k}"]`, false));

    // show matching specific section only for SEA/AIR/INLAND
    if (SPEC.includes(group)) {
      show(`[data-booking-section="${group}"]`, true);
    }
  }

  document.addEventListener("change", function (e) {
    if (e.target && (e.target.id === "id_booking_group" || e.target.name === "booking_group")) {
      toggleByBookingGroup();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    toggleByBookingGroup();
  });
})();
