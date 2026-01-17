(function () {
  function $(s, r) { return (r || document).querySelector(s); }
  function $all(s, r) { return Array.from((r || document).querySelectorAll(s)); }

  const tbody = $("#lines-table tbody");
  if (!tbody) return;

  const btnAdd = $("#vbAddLineBtn");
  const btnLoad = $("#vbLoadFromJobCostBtn");

  const jobOrderEl = $("#id_job_order");
  const groupEl = $("#id_booking_group");

  const modalEl = $("#vbJobCostModal");
  const jcTbody = $("#vbJobCostTbody");
  const jcErr = $("#vbJobCostErr");
  const jcApply = $("#vbJobCostApplyBtn");
  const jcCheckAll = $("#vbJcCheckAll");

  const totalEl = $('input[name$="-TOTAL_FORMS"]');
  if (!totalEl) {
    console.warn("TOTAL_FORMS not found (formset).");
    return;
  }

  function showErr(msg) {
    if (!jcErr) return;
    jcErr.textContent = msg || "";
    jcErr.classList.toggle("d-none", !msg);
  }

  function esc(s) {
    return String(s || "")
      .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  }

  function buildRow(index) {
    const tpl = $("#vb-line-template");
    if (!tpl) throw new Error("Template row (#vb-line-template) tidak ditemukan.");
    const html = tpl.innerHTML.replaceAll("__prefix__", String(index));
    const tr = document.createElement("tr");
    tr.className = "vb-line-row";
    tr.innerHTML = html;
    bindRow(tr);
    return tr;
  }

  function addRow() {
    const idx = parseInt(totalEl.value || "0", 10);
    const tr = buildRow(idx);
    tbody.appendChild(tr);
    totalEl.value = String(idx + 1);
    return tr;
  }

  function bindRow(tr) {
    const rm = tr.querySelector(".vb-remove-line");
    if (rm) {
      rm.addEventListener("click", function () {
        const del = tr.querySelector('input[type="checkbox"][name$="-DELETE"]');
        if (del) {
          del.checked = true;
          tr.classList.add("d-none");
        } else {
          tr.remove();
        }
      });
    }

    // auto calc amount
    const qty = tr.querySelector('[name$="-qty"]');
    const up = tr.querySelector('[name$="-unit_price"]');
    const amt = tr.querySelector('[name$="-amount"]');

    function recalc() {
      if (!amt) return;
      const q = parseFloat(qty?.value || "0") || 0;
      const p = parseFloat(up?.value || "0") || 0;
      amt.value = (q * p).toFixed(2);
      amt.dispatchEvent(new Event("input", { bubbles: true }));
    }

    qty?.addEventListener("input", recalc);
    up?.addEventListener("input", recalc);
  }

  // bind existing rows
  $all("#lines-table tbody tr.vb-line-row").forEach(bindRow);

  btnAdd?.addEventListener("click", function () {
    try { addRow(); } catch (e) { console.error(e); }
  });

  async function fetchJobCosts(jobOrderId, bookingGroup) {
    const url = `${window.VB_JOBCOST_URL}?job_order=${encodeURIComponent(jobOrderId)}&booking_group=${encodeURIComponent(bookingGroup)}`;
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.error || "Gagal load Job Cost.");
    return data.items || [];
  }

  function openModal() {
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function renderJobCost(items) {
    if (!items.length) {
      jcTbody.innerHTML = `<tr><td colspan="5" class="text-muted small py-3">Tidak ada cost untuk group ini.</td></tr>`;
      return;
    }
    jcTbody.innerHTML = items.map((it) => `
      <tr data-jc="${esc(JSON.stringify(it))}">
        <td><input type="checkbox" class="vb-jc-check" checked></td>
        <td class="small fw-semibold">${esc(it.cost_type_name)}</td>
        <td class="small">${esc(it.description)}</td>
        <td class="text-end small">${esc(String(it.qty ?? 1))}</td>
        <td class="small">${esc(it.uom || "")}</td>
      </tr>
    `).join("");
  }

  function parseJC(tr) {
    const raw = tr.getAttribute("data-jc") || "";
    try {
      const s = raw
        .replaceAll("&quot;", '"').replaceAll("&#039;", "'")
        .replaceAll("&gt;", ">").replaceAll("&lt;", "<").replaceAll("&amp;", "&");
      return JSON.parse(s);
    } catch { return null; }
  }

  function lockGroupIfHasCostType() {
    if (!groupEl) return;
    const has = $all("#lines-table tbody tr").some(tr => {
      const sel = tr.querySelector('select[name$="-cost_type"]');
      return sel && sel.value;
    });
    if (has) groupEl.setAttribute("disabled", "disabled");
  }

  btnLoad?.addEventListener("click", async function () {
    showErr("");
    const jobOrderId = (jobOrderEl?.value || "").trim();
    const grp = (groupEl?.value || "").trim();

    if (!jobOrderId) { showErr("Pilih Job Order dulu."); openModal(); return; }
    if (!grp) { showErr("Pilih Booking Group dulu."); openModal(); return; }

    jcTbody.innerHTML = `<tr><td colspan="5" class="text-muted small py-3">Loading…</td></tr>`;
    openModal();

    try {
      const items = await fetchJobCosts(jobOrderId, grp);
      renderJobCost(items);
      if (jcCheckAll) jcCheckAll.checked = true;
    } catch (e) {
      showErr(e.message || "Gagal load.");
    }
  });

  jcCheckAll?.addEventListener("change", function () {
    $all(".vb-jc-check", modalEl).forEach(cb => cb.checked = jcCheckAll.checked);
  });

  jcApply?.addEventListener("click", function () {
    showErr("");

    const selected = $all("#vbJobCostTbody tr")
      .filter(tr => tr.querySelector(".vb-jc-check")?.checked)
      .map(parseJC)
      .filter(Boolean);

    if (!selected.length) { showErr("Pilih minimal 1 item."); return; }

    selected.forEach((it) => {
      const tr = addRow();

      // set cost_type
      const sel = tr.querySelector('select[name$="-cost_type"]');
      if (sel) {
        sel.value = String(it.cost_type_id || "");
        sel.dispatchEvent(new Event("change", { bubbles: true }));
      }

      // set description/qty/uom/job_cost_id
      const desc = tr.querySelector('[name$="-description"]');
      const qty = tr.querySelector('[name$="-qty"]');
      const uom = tr.querySelector('[name$="-uom"]');
      const jc = tr.querySelector('[name$="-job_cost_id"]');

      if (desc) desc.value = it.description || it.cost_type_name || "";
      if (qty) qty.value = String(it.qty ?? 1);
      if (uom) uom.value = it.uom || "";
      if (jc) jc.value = String(it.job_cost_id || "");

      desc?.dispatchEvent(new Event("input", { bubbles: true }));
      qty?.dispatchEvent(new Event("input", { bubbles: true }));
    });

    lockGroupIfHasCostType();
    bootstrap.Modal.getInstance(modalEl)?.hide();
  });

})();
