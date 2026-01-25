(function () {
  function initTaxSelect2(scope) {
    const root = scope && scope.querySelectorAll ? scope : document;
    const selects = root.querySelectorAll('select[name$="-taxes"]');
    if (!selects.length) return;

    if (!window.jQuery?.fn?.select2) {
      console.warn("initTaxSelect2: select2 belum loaded");
      return;
    }

    selects.forEach(function (el) {
      const $el = window.jQuery(el);

      // destroy kalau sudah ada (optional) — biar aman kalau re-init
      if ($el.data("select2")) return;

      const modal = el.closest(".modal");

      $el.select2({
        width: "100%",
        dropdownParent: modal ? window.jQuery(modal) : window.jQuery(document.body),
      });

      // ✅ INI KUNCI: class yang dibutuhkan CSS lama
      const $container = $el.next(".select2-container");
      if ($container.length) {
        $container.addClass("tax-badge-container");
      }
    });
  }

  window.initTaxSelect2 = initTaxSelect2;
})();
