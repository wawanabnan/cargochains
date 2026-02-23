(function (window) {

  let TAX_MAP = {};

  function readTaxMap() {
    const el = document.getElementById("tax-map");
    if (!el) return {};
    try { return JSON.parse(el.textContent); } catch { return {}; }
  }

  function getSelectedTaxIds(){
    const sel = document.getElementById("id_taxes");
    if(!sel) return [];
    return Array.from(sel.selectedOptions || []).map(o=>o.value).filter(Boolean);
  }

  function computeTaxes(base){

  const taxIds = getSelectedTaxIds();

  let vat = 0;

  taxIds.forEach((id) => {
    const t = TAX_MAP[String(id)];
    if (!t) return;

    // abaikan withholding
    if (t.is_withholding) return;

    const r = (Number(t.rate || 0) / 100.0);
    vat += base * r;
  });

  return { vat };
}

  document.addEventListener("DOMContentLoaded", function () {
    TAX_MAP = readTaxMap();
  });

  window.JobTax = {
    computeTaxes
  };

})(window);