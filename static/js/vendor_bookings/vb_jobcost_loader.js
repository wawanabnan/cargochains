(function () {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  // Always read latest Job Order id
  function getJobOrderId() {
    // priority: global var updated by template script
    if (typeof window.VB_JOB_ORDER_ID !== "undefined" && window.VB_JOB_ORDER_ID !== null) {
      return String(window.VB_JOB_ORDER_ID || "");
    }
    // fallback: read from DOM directly
    if (typeof window.vbReadJobOrderId === "function") {
      return String(window.vbReadJobOrderId() || "");
    }
    const el =
      qs('select[name$="job_order"]') ||
      qs('input[name$="job_order"]') ||
      qs('#id_job_order');
    return el ? String(el.value || "") : "";
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function fmt(x) {
    const n = Number(x || 0);
    return n.toLocaleString("id-ID", { maximumFractionDigits: 2 });
  }

  async function fetchJson(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) {
      const msg = data.error || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  // ---------- Formset helpers ----------
  function getTotalFormsEl() {
    return qs('input[name$="-TOTAL_FORMS"]') || qs('input[id$="-TOTAL_FORMS"]');
  }

  function getFormPrefix() {
    const el = getTotalFormsEl();
    if (!el) return null;
    const name = el.getAttribute("name") || "";
    return name.replace("-TOTAL_FORMS", "");
  }

  function getTbodyLines() {
    const t = qs("#lines-table");
    return t ? qs("tbody", t) : null;
  }

  function ensureEmptyFormTemplateExists() {
    // we read from #vb-empty-line-raw
    if (qs("#vb-empty-line-raw")) return true;
    console.error("Missing #vb-empty-line-raw (empty form html) in template.");
    return false;
  }

  function addEmptyRow(prefix) {
    const tbody = getTbodyLines();
    if (!tbody) return null;

    const totalEl = getTotalFormsEl();
    if (!totalEl) {
      console.error("TOTAL_FORMS not found");
      return null;
    }

    const total = parseInt(totalEl.value || "0", 10);

    const raw = qs("#vb-empty-line-raw");
    if (!raw) return null;

    let html = raw.innerHTML.trim();
    html = html.replaceAll("__prefix__", String(total));

    const temp = document.createElement("tbody");
    temp.innerHTML = html;
    const row = temp.querySelector("tr");
    if (!row) return null;

    tbody.appendChild(row);

    totalEl.value = String(total + 1);
    totalEl.dispatchEvent(new Event("change", { bubbles: true }));

    return row;
  }

  function setRowField(row, suffix, value) {
    if (!row) return;
    const el = row.querySelector(`[name$="${suffix}"]`);
    if (!el) return;
    el.value = value ?? "";
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function clearExistingLinesSoft() {
    // mark DELETE if exists; otherwise remove row
    const tbody = getTbodyLines();
    if (!tbody) return;

    qsa("tr", tbody).forEach(tr => {
      const del = tr.querySelector('input[name$="-DELETE"]');
      if (del) {
        del.checked = true;
        tr.classList.add("d-none");
      } else {
        tr.remove();
      }
    });
  }

  // ---------- Modal elements ----------
  const elModal = qs("#vbJobCostModal");
  if (!elModal) return;

  const URL_VENDOR = window.VB_JOBCOST_VENDOR_URL;
  const URL_JOBCOST = window.VB_JOBCOST_URL;

  const elVendor = qs("#vbJobCostVendor");
  const elGroup = qs("#vbJobCostGroup");
  const elTbody = qs("#vbJobCostTbody");
  const elApply = qs("#vbJobCostApplyBtn");

  if (!URL_VENDOR || !URL_JOBCOST) {
    console.error("Missing VB_JOBCOST_VENDOR_URL / VB_JOBCOST_URL");
    return;
  }

  function setApplyEnabled() {
    const checked = qsa('input.vb-jc-check:checked', elTbody).length;
    elApply.disabled = checked <= 0;
  }

  function renderJobCosts(items) {
    elTbody.innerHTML = "";
    items = items || [];

    if (!items.length) {
      elTbody.innerHTML = `<tr><td colspan="6" class="text-muted small py-3">Tidak ada Job Cost OPEN untuk filter ini.</td></tr>`;
      elApply.disabled = true;
      return;
    }

    for (const it of items) {
      const open = Number(it.open || 0);
      const disabled = open <= 0;

      const tr = document.createElement("tr");
      tr.dataset.jobCostId = String(it.job_cost_id);
      tr.dataset.costTypeId = String(it.cost_type_id);
      tr.dataset.description = it.description || "";
      tr.dataset.open = String(open);

      tr.innerHTML = `
        <td class="text-center">
          <input class="form-check-input vb-jc-check" type="checkbox" ${disabled ? "disabled" : ""}>
        </td>
        <td class="small">${escapeHtml(it.cost_type_name || "")}</td>
        <td class="small">${escapeHtml(it.description || "")}</td>
        <td class="text-end small">${fmt(it.qty)}</td>
        <td class="text-end small">${fmt(it.allocated)}</td>
        <td class="text-end small">${fmt(it.open)}</td>
      `;

      if (disabled) tr.classList.add("table-secondary");

      const cb = tr.querySelector("input.vb-jc-check");
      cb.addEventListener("change", setApplyEnabled);

      elTbody.appendChild(tr);
    }

    elApply.disabled = true;
  }

  async function loadVendors() {
    const jo = getJobOrderId();
    if (!jo) {
      elVendor.innerHTML = `<option value="">(pilih Job Order dulu)</option>`;
      return;
    }

    const url = `${URL_VENDOR}?job_order=${encodeURIComponent(jo)}`;
    const data = await fetchJson(url);

    elVendor.innerHTML = `<option value="">-- pilih vendor --</option>`;
    (data.items || []).forEach(v => {
      const opt = document.createElement("option");
      opt.value = String(v.id);
      opt.textContent = v.name;
      elVendor.appendChild(opt);
    });
  }

  async function loadJobCosts() {
    const jo = getJobOrderId();
    if (!jo) {
      elTbody.innerHTML = `<tr><td colspan="6" class="text-muted small py-3">Pilih Job Order dulu.</td></tr>`;
      elApply.disabled = true;
      return;
    }

    const vendorId = elVendor.value;
    if (!vendorId) {
      elTbody.innerHTML = `<tr><td colspan="6" class="text-muted small py-3">Pilih vendor dulu.</td></tr>`;
      elApply.disabled = true;
      return;
    }

    const params = new URLSearchParams({
      job_order: jo,
      vendor: vendorId,
    });

    if (elGroup && elGroup.value) params.set("booking_group", elGroup.value);

    const url = `${URL_JOBCOST}?${params.toString()}`;
    const data = await fetchJson(url);

    renderJobCosts(data.items || []);
  }

  function applySelected() {
    const prefix = getFormPrefix();
    if (!prefix) {
      alert("Formset TOTAL_FORMS tidak ditemukan.");
      return;
    }
    if (!ensureEmptyFormTemplateExists()) {
      alert("Template empty form tidak ditemukan (#vb-empty-line-raw).");
      return;
    }

    // optional: clear existing lines first (biar tidak dobel)
    clearExistingLinesSoft();

    const selected = qsa("tr", elTbody).filter(tr => {
      const cb = tr.querySelector("input.vb-jc-check");
      return cb && cb.checked && !cb.disabled;
    });

    if (!selected.length) return;

    for (const tr of selected) {
      const row = addEmptyRow(prefix);
      if (!row) continue;

      const jobCostId = tr.dataset.jobCostId;
      const costTypeId = tr.dataset.costTypeId;
      const desc = tr.dataset.description || "";
      const openQty = Number(tr.dataset.open || 0);

      setRowField(row, "-job_cost", jobCostId);
      setRowField(row, "-cost_type", costTypeId);
      setRowField(row, "-description", desc);
      setRowField(row, "-qty", openQty > 0 ? openQty : 1);
    }

    const bsModal = bootstrap.Modal.getInstance(elModal);
    if (bsModal) bsModal.hide();
  }

  // ---------- Bind ----------
  elVendor.addEventListener("change", loadJobCosts);
  if (elGroup) elGroup.addEventListener("change", loadJobCosts);
  elApply.addEventListener("click", applySelected);

  // reload vendors each time modal opened (job order bisa berubah)
  elModal.addEventListener("show.bs.modal", async function () {
    try {
      await loadVendors();
      elTbody.innerHTML = `<tr><td colspan="6" class="text-muted small py-3">Pilih vendor untuk melihat Job Cost.</td></tr>`;
      elApply.disabled = true;
    } catch (e) {
      elTbody.innerHTML = `<tr><td colspan="6" class="text-danger small py-3">${escapeHtml(e.message)}</td></tr>`;
      elApply.disabled = true;
    }
  });
  
  document.addEventListener("DOMContentLoaded", function () {
  const modalEl = document.getElementById("vbJobCostModal");
  if (!modalEl) return;

  // jika modal tidak langsung di body, pindahkan
  if (modalEl.parentElement !== document.body) {
    document.body.appendChild(modalEl);
    console.log("vbJobCostModal moved to <body>");
  }
});


})();
