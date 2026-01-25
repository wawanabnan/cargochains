(function () {

  function renderTaxBadge(tax, forSelection = false) {
    if (!tax.id) return tax.text;

    // Ambil metadata dari <option data-*>
    const type = tax.element?.dataset?.type || "";   // misal: tax / pph
    const rate = tax.element?.dataset?.rate || "";   // misal: 1.1%
    const color = tax.element?.dataset?.color || ""; // optional

    let badgeClass = "badge bg-secondary";
    if (type === "pph") badgeClass = "badge bg-warning text-dark";
    if (type === "tax") badgeClass = "badge bg-success";

    const $badge = document.createElement("span");
    $badge.className = badgeClass;
    $badge.textContent = tax.text + (rate ? ` (${rate})` : "");

    // untuk selection: padding kecil biar inline rapi
    if (forSelection) {
      $badge.style.marginRight = "4px";
    }

    return $badge;
  }

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

      // Jangan init ulang
      if ($el.data("select2")) return;

      const modal = el.closest(".modal");

      $el.select2({
        width: "100%",
        dropdownParent: modal
          ? window.jQuery(modal)
          : window.jQuery(document.body),

        closeOnSelect: false, // multi-select UX lebih enak

        templateResult: function (data) {
          return renderTaxBadge(data, false);
        },

        templateSelection: function (data) {
          return renderTaxBadge(data, true);
        },

        escapeMarkup: function (m) {
          return m;
        },
      });

      // class container biar CSS lama vendor booking tetap kepake
      const $container = $el.next(".select2-container");
      if ($container.length) {
        $container.addClass("tax-badge-container");
      }
    });
  }

  window.initTaxSelect2 = initTaxSelect2;

})();
