document.addEventListener("DOMContentLoaded", function () {
  window.VBLines = window.VBLines || { plugins: [] };

  function autoGrowTextarea(el) {
    try {
      el.style.height = "auto";
      el.style.height = el.scrollHeight + "px";
    } catch (e) {}
  }

  function bindAutoGrowRow(tr) {
    tr.querySelectorAll("textarea.auto-grow").forEach((ta) => {
      if (ta.dataset.vbAutogrowBound) return;
      ta.dataset.vbAutogrowBound = "1";

      autoGrowTextarea(ta);
      ta.addEventListener("input", function () {
        autoGrowTextarea(ta);
      });
    });
  }

  window.VBLines.plugins.push({
    onInit({ tbody }) {
      tbody.querySelectorAll("tr").forEach(bindAutoGrowRow);
    },
    onRowAdded(tr) {
      bindAutoGrowRow(tr);
    },
  });
});
