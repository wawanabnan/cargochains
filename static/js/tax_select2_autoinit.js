(function () {
  function initTaxSelect2(scope) {
    const root = scope && scope.querySelectorAll ? scope : document;

    // Selector dibuat super fleksibel (form biasa & formset)
    const selects = root.querySelectorAll(
      'select[name="taxes"], select#id_taxes, select[name$="-taxes"], select[name$="taxes"]'
    );
    if (!selects.length) return;

    if (!window.jQuery?.fn?.select2) {
      console.warn("initTaxSelect2: select2 belum loaded");
      return;
    }

    selects.forEach(function (el) {
      const $el = window.jQuery(el);

      // destroy kalau sudah ada (biar bisa re-init kalau perlu)
      if ($el.data("select2")) return;

      const modal = el.closest(".modal");

      $el.select2({
        width: "100%",
        dropdownParent: modal ? window.jQuery(modal) : window.jQuery(document.body),
        closeOnSelect: false, // kalau multi select
      });

      // class untuk CSS badge container (vendor booking)
      const $container = $el.next(".select2-container");
      if ($container.length) {
        $container.addClass("tax-badge-container");
      }
    });
  }

  // expose
  window.initTaxSelect2 = initTaxSelect2;

  // ✅ AUTO INIT (nggak tergantung inline JS location)
  function boot() {
    initTaxSelect2(document);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
