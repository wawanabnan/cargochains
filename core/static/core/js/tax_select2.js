(function () {
  // ---- helpers: format rate + label by code ----
  function fmtRate(text) {
    if (!text) return "";
    const m = String(text).match(/([\d.]+)\s*%/);
    if (!m) return String(text).trim();
    const n = parseFloat(m[1]);
    if (Number.isNaN(n)) return String(text).trim();
    // 1.10 -> 1.1 ; 2.00 -> 2
    return n.toString() + "%";
  }

  function labelByCode(data) {
    if (!data) return "";
    const rawText = data.text || "";
    const rate = fmtRate(rawText);

    const opt = data.element; // <option>
    const code = opt && opt.dataset ? (opt.dataset.code || "") : "";
    if (!code) return rate || rawText;

    const upper = code.toUpperCase();

    // PPH_23 -> "PPh 23 (2%)"
    if (upper.startsWith("PPH")) {
      const pasal = upper.replace("PPH_", "").replace(/^_/, "");
      return pasal ? `PPh ${pasal} (${rate})` : `PPh (${rate})`;
    }

    // PPN_JT / PPN_TS -> "PPN 1.1%"
    if (upper.startsWith("PPN")) {
      return `PPN ${rate}`;
    }

    // fallback: tampilkan code + rate
    return `${code} ${rate}`.trim();
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

      // ✅ jangan double init
      if ($el.data("select2")) return;

      const modal = el.closest(".modal");

      $el.select2({
        width: "100%",
        closeOnSelect: false, // multi-select UX lebih enak
        dropdownParent: modal ? window.jQuery(modal) : window.jQuery(document.body),

        // ✅ Badge (selected items)
        templateSelection: function (data) {
          // placeholder item
          if (!data.id) return data.text;

          const span = document.createElement("span");
          span.textContent = labelByCode(data);
          return span;
        },

        // ✅ Dropdown list (opsional tapi bagus biar konsisten)
        templateResult: function (data) {
          if (!data.id) return data.text;
          return labelByCode(data);
        },
      });

      // ✅ class untuk styling container (CSS kamu)
      const $container = $el.next(".select2-container");
      if ($container.length) {
        $container.addClass("tax-badge-container");
      }
    });
  }

  window.initTaxSelect2 = initTaxSelect2;
})();
