document.addEventListener("DOMContentLoaded", function () {
  window.VBLines = window.VBLines || { plugins: [] };

  function isExistingRow(tr) {
    const id = tr.querySelector('input[name$="-id"]');
    return !!(id && String(id.value || "").trim());
  }

  function detectPrefixFromTotalForms(totalForms) {
    if (!totalForms || !totalForms.id) return null;
    return totalForms.id.replace(/^id_/, "").replace(/-TOTAL_FORMS$/, "");
  }

  function renumberFormset(tbody, totalForms) {
    const prefix = detectPrefixFromTotalForms(totalForms);
    if (!prefix) return;

    const rows = Array.from(tbody.querySelectorAll("tr")).filter((tr) => !tr.classList.contains("d-none"));
    rows.forEach((tr, i) => {
      tr.querySelectorAll("input,select,textarea,label").forEach((el) => {
        if (el.name) el.name = el.name.replace(new RegExp(`^${prefix}-\\d+-`), `${prefix}-${i}-`);
        if (el.id) el.id = el.id.replace(new RegExp(`^id_${prefix}-\\d+-`), `id_${prefix}-${i}-`);
        if (el.htmlFor) el.htmlFor = el.htmlFor.replace(new RegExp(`^id_${prefix}-\\d+-`), `id_${prefix}-${i}-`);
      });
    });

    totalForms.value = String(rows.length);
  }

  function upgradeDeleteUI(tr) {
    const cb = tr.querySelector('input[type="checkbox"][name$="-DELETE"]');
    if (!cb) return;

    cb.classList.add("d-none");

    const cell = cb.closest("td") || tr.lastElementChild;
    if (!cell) return;

    if (cell.querySelector(".vb-line-del-btn")) return;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-outline-danger btn-sm py-0 px-2 vb-line-del-btn";
    btn.innerHTML = '<i class="bi bi-trash"></i>';
    btn.title = "Delete line";

    cell.appendChild(btn);
  }

  function bindDeleteDelegationOnce() {
    if (document.body.dataset.vbDelBound) return;
    document.body.dataset.vbDelBound = "1";

    document.addEventListener("click", function (e) {
      const btn = e.target.closest(".vb-line-del-btn");
      if (!btn) return;

      e.preventDefault();

      const tr = btn.closest("tr");
      if (!tr) return;

      // cari context table
      const tbody = tr.closest("tbody");
      const totalForms = document.querySelector('input[id$="-TOTAL_FORMS"]');
      const cb = tr.querySelector('input[type="checkbox"][name$="-DELETE"]');

      if (isExistingRow(tr)) {
        if (cb) cb.checked = true;
        tr.classList.add("d-none");
      } else {
        tr.remove();
        if (tbody && totalForms) renumberFormset(tbody, totalForms);
      }
    });
  }

  window.VBLines.plugins.push({
    onInit({ tbody }) {
      bindDeleteDelegationOnce();
      tbody.querySelectorAll("tr").forEach(upgradeDeleteUI);
    },
    onRowAdded(tr) {
      bindDeleteDelegationOnce();
      upgradeDeleteUI(tr);
    },
  });
});
