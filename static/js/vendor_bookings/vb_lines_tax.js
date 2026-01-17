document.addEventListener("DOMContentLoaded", function () {
  window.VBLines = window.VBLines || { plugins: [] };

  function safeInitTax(scope) {
    if (typeof window.initTaxSelect2 === "function") {
      try {
        window.initTaxSelect2(scope);
      } catch (e) {
        console.warn("initTaxSelect2 error:", e);
      }
    }
  }

  window.VBLines.plugins.push({
    onInit({ tbody }) {
      safeInitTax(tbody);
    },
    onRowAdded(tr) {
      safeInitTax(tr);
    },
  });
});
