/* static/vendor_bookings/vb_lines_controller.js
   Vendor Booking Lines Controller (cleaned)

   Goals:
   - Require booking_group before adding line (enable/disable button + guard)
   - Add new formset row from #empty-line-row template
   - Set default cost_type on new row:
       1) copy previous row cost_type if exists
       2) fallback by booking_group from:
          a) btnAdd.dataset.defaultCtMap (JSON) if provided
          b) window.VB.costTypes (first match by cost_group)

   Notes:
   - Requires DOM:
       #btn-add-line
       #lines-table tbody
       input[name$="-TOTAL_FORMS"] or input[id$="-TOTAL_FORMS"]
       #empty-line-row (innerHTML contains __prefix__)
*/
document.addEventListener("DOMContentLoaded", function () {
  // -----------------------------
  // DOM refs
  // -----------------------------
  const btnAdd = document.getElementById("btn-add-line");
  const tbody = document.querySelector("#lines-table tbody");
  const totalForms =
    document.querySelector('input[name$="-TOTAL_FORMS"]') ||
    document.querySelector('input[id$="-TOTAL_FORMS"]');
  const tmpl = document.getElementById("empty-line-row");
  const bookingGroupEl = document.getElementById("id_booking_group");

  if (!btnAdd || !tbody || !totalForms || !tmpl) {
    console.warn("VBLines: element tidak lengkap", { btnAdd, tbody, totalForms, tmpl });
    return;
  }

  // -----------------------------
  // Helpers
  // -----------------------------
  function getBookingGroup() {
    return bookingGroupEl ? String(bookingGroupEl.value || "").trim() : "";
  }

  function parseJSONSafe(s, fallback = {}) {
    try {
      const o = JSON.parse(s);
      return o && typeof o === "object" ? o : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function findCostTypeEl(row) {
    return row.querySelector('input[name$="-cost_type"], select[name$="-cost_type"]');
  }

  function findDetailsEl(row) {
    // hidden details json (sesuaikan jika namanya beda)
    return row.querySelector('input[name$="-details"]');
  }

  function rowIsLocked(row) {
    // "minimal ada 1 line cost_type_id hidden sudah terisi"
    // kita anggap locked jika:
    // - cost_type ada nilainya, ATAU
    // - details json bukan "{}"
    const ctEl = findCostTypeEl(row);
    const ct = ctEl ? String(ctEl.value || "").trim() : "";
    if (ct) return true;

    const detEl = findDetailsEl(row);
    const raw = detEl ? String(detEl.value || "").trim() : "";
    if (!raw) return false;

    // treat "{}" or empty object as not locked
    const obj = parseJSONSafe(raw, {});
    return Object.keys(obj || {}).length > 0;
  }

  function anyRowLocked() {
    const rows = tbody.querySelectorAll("tr");
    for (const tr of rows) {
      if (rowIsLocked(tr)) return true;
    }
    return false;
  }

  function lockBookingGroupIfNeeded() {
    if (!bookingGroupEl) return;
    const locked = anyRowLocked();

    // kalau ada minimal 1 row locked -> disable dropdown
    bookingGroupEl.disabled = locked;

    // simpan flag utk info UX (optional)
    bookingGroupEl.dataset.vbLocked = locked ? "1" : "0";
  }

  function syncAddButton() {
    // jika group kosong -> tombol add disabled
    const group = getBookingGroup();
    btnAdd.disabled = !group;
  }

  function copyPrevCostType(row) {
    const prev = row.previousElementSibling;
    if (!prev) return "";
    const prevCT = findCostTypeEl(prev);
    const v = prevCT && prevCT.value ? String(prevCT.value).trim() : "";
    return v || "";
  }

  function getDefaultCtMapFromButton() {
    // optional: data-default-ct-map='{"SEA":3,"AIR":4,...}'
    const raw = btnAdd?.dataset?.defaultCtMap || "";
    if (!raw) return {};
    return parseJSONSafe(raw, {});
  }

  function getDefaultCostTypeIdByGroup(group) {
    if (!group) return "";

    // 1) dataset map (paling deterministic)
    const map = getDefaultCtMapFromButton();
    if (map && map[group]) return String(map[group]);

    // 2) fallback: window.VB.costTypes (first match)
    const list = window.VB && Array.isArray(window.VB.costTypes) ? window.VB.costTypes : [];
    const ct = list.find((x) => x && String(x.cost_group || "") === group);
    return ct ? String(ct.id) : "";
  }

  // -----------------------------
  // Plugin registry (optional)
  // -----------------------------
  window.VBLines = window.VBLines || { plugins: [] };

  function callPlugins(fn, ...args) {
    (window.VBLines.plugins || []).forEach((p) => {
      if (p && typeof p[fn] === "function") {
        try {
          p[fn](...args);
        } catch (e) {
          console.warn("VBLines plugin error:", fn, e);
        }
      }
    });
  }

  // -----------------------------
  // Single plugin: default cost_type on row added
  // (register ONCE)
  // -----------------------------
  if (!window.VBLines.__defaultCtPluginBound) {
    window.VBLines.__defaultCtPluginBound = true;

    window.VBLines.plugins.push({
      onRowAdded(newRow, ctx) {
        const ctEl = findCostTypeEl(newRow);
        if (!ctEl) return;

        // reset details for new row
        const detEl = findDetailsEl(newRow);
        if (detEl) detEl.value = "{}";

        // don't override if already set
        if (String(ctEl.value || "").trim()) return;

        // 1) copy from previous row (requirement #2)
        const prevVal = copyPrevCostType(newRow);
        if (prevVal) {
          ctEl.value = prevVal;
          ctEl.dispatchEvent(new Event("change", { bubbles: true }));
          return;
        }

        // 2) fallback by booking_group
        const group = ctx?.getBookingGroup ? ctx.getBookingGroup() : getBookingGroup();
        const defId = getDefaultCostTypeIdByGroup(group);
        if (defId) {
          ctEl.value = defId;
          ctEl.dispatchEvent(new Event("change", { bubbles: true }));
        }
      },
    });
  }

  // -----------------------------
  // Init existing rows once
  // -----------------------------
  callPlugins("onInit", { tbody, totalForms, tmpl, btnAdd });

  // -----------------------------
  // Add Line click (bind ONCE)
  // -----------------------------
  if (!btnAdd.dataset.vbBoundAddLine) {
    btnAdd.dataset.vbBoundAddLine = "1";

    btnAdd.addEventListener("click", function (e) {
      const group = getBookingGroup();
      if (!group) {
        e.preventDefault();
        e.stopPropagation();
        alert("Pilih Booking Type dulu sebelum menambah line.");
        return;
      }

      // create new row from template
      const idx = parseInt(totalForms.value || "0", 10);
      const html = (tmpl.innerHTML || "").replace(/__prefix__/g, String(idx));
      if (!html.trim()) {
        console.warn("VBLines: empty template");
        return;
      }

      tbody.insertAdjacentHTML("beforeend", html);
      totalForms.value = String(idx + 1);

      const newRow = tbody.lastElementChild;
      if (!newRow) return;

      newRow.dataset.vbRow = "1";

      // notify plugins
      callPlugins("onRowAdded", newRow, {
        tbody,
        totalForms,
        tmpl,
        btnAdd,
        getBookingGroup,
      });

      // requirement #1: setelah ada line (dan cost_type nanti terisi),
      // kita lock booking group berdasarkan kondisi row locked
      lockBookingGroupIfNeeded();
    });
  }

  // -----------------------------
  // Enable/disable add button by booking_group
  // -----------------------------
  syncAddButton();
  if (bookingGroupEl && !bookingGroupEl.dataset.vbBoundSyncAdd) {
    bookingGroupEl.dataset.vbBoundSyncAdd = "1";

    // simpan previous value (untuk safety)
    bookingGroupEl.dataset.prevValue = bookingGroupEl.value || "";

    bookingGroupEl.addEventListener("change", function () {
      // kalau sudah terkunci, revert (double safety)
      if (anyRowLocked()) {
        alert("Booking Type tidak bisa diubah karena sudah ada line yang Cost Type / Detail-nya terisi.");
        bookingGroupEl.value = bookingGroupEl.dataset.prevValue || "";
        return;
      }

      bookingGroupEl.dataset.prevValue = bookingGroupEl.value || "";
      syncAddButton();
    });
  }

  // -----------------------------
  // Lock booking group on page load (edit mode)
  // -----------------------------
  lockBookingGroupIfNeeded();

  // -----------------------------
  // Lock booking group whenever a cost_type is changed in any row
  // (covers: modal OK sets cost_type, manual edit, etc.)
  // -----------------------------
  document.addEventListener("change", function (e) {
    const el = e.target;
    if (!el) return;
    if (!el.matches('input[name$="-cost_type"], select[name$="-cost_type"]')) return;
    lockBookingGroupIfNeeded();
  });
});
