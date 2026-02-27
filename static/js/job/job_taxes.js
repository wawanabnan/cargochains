(function (window) {

  let TAX_MAP = {};

  function readTaxMap() {
    const el = document.getElementById("tax-map");
    if (!el) return {};
    try { 
      return JSON.parse(el.textContent); 
    } catch { 
      return {}; 
    }
  }

  function getSelectedTaxIds(){
    const sel = document.getElementById("id_taxes");
    if (!sel) return [];
    return Array.from(sel.selectedOptions || [])
      .map(o => o.value)
      .filter(Boolean);
  }

  function computeTaxes(base){

    const taxIds = getSelectedTaxIds();
    let vat = 0;

    taxIds.forEach((id) => {
      const t = TAX_MAP[String(id)];
      if (!t) return;

      // skip withholding
      if (t.is_withholding) return;

      const r = (Number(t.rate || 0) / 100.0);
      vat += base * r;
    });

    return { vat };
  }

  function attachListeners() {

    const taxesEl = document.getElementById("id_taxes");
    const $ = window.jQuery;

    if (!taxesEl) return;

    function triggerRecalc() {
      if (window.JobCalc && window.JobCalc.recalc) {
        window.JobCalc.recalc();
      }
    }

    // Native change
    taxesEl.addEventListener("change", triggerRecalc);

    // Select2 support
    if ($ && $.fn.select2) {
      $(taxesEl).on("select2:select select2:unselect", triggerRecalc);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    TAX_MAP = readTaxMap();
    console.log("TAX_MAP loaded:", TAX_MAP);

    attachListeners();
  });

  window.JobTax = {
    computeTaxes
  };

})(window);