(function () {

  function initTaxSelect2(scope) {

    const root = scope && scope.querySelectorAll ? scope : document;
    const selects = root.querySelectorAll('select[name$="-taxes"]');
    if (!selects.length) return;

    const taxMapEl = document.getElementById("tax-map");
    const TAX_MAP = taxMapEl ? JSON.parse(taxMapEl.textContent || "{}") : {};

    function formatOption(option) {
      if (!option.id) return option.text;

      const tax = TAX_MAP[String(option.id)];
      if (!tax) return option.text;

      const badgeClass = tax.is_withholding
        ? "badge bg-danger"
        : "badge bg-primary";

      return $('<span class="' + badgeClass + '">' + option.text + '</span>');
    }

    selects.forEach(function (el) {

      const $el = window.jQuery(el);

      // 🔥 FORCE override config lama
      if ($el.data('select2')) {
        $el.select2('destroy');
      }

      $el.select2({
        width: '100%',
        templateResult: formatOption,
        templateSelection: formatOption,
        escapeMarkup: function (m) { return m; }
      });

    });
  }

  window.initTaxSelect2 = initTaxSelect2;

})();