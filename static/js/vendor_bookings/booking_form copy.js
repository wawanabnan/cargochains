document.addEventListener("DOMContentLoaded", function () {
  // ---- Transport toggle (tab Locations) ----
  function setLocationsVisible(yes) {
    const tabBtn = document.getElementById("tab-locations");
    const pane = document.getElementById("pane-locations");

    if (tabBtn && tabBtn.parentElement) tabBtn.parentElement.classList.toggle("d-none", !yes);
    if (pane) pane.classList.toggle("d-none", !yes);

    if (!yes) {
      const activePane = document.querySelector("#vbTabsContent .tab-pane.active");
      if (activePane && activePane.id === "pane-locations") {
        document.getElementById("tab-general")?.click();
      }
    }
  }

  const cb = document.getElementById("id_is_transport");
  if (cb) {
    setLocationsVisible(cb.checked);
    cb.addEventListener("change", () => setLocationsVisible(cb.checked));
  }

  // ---- Add Line (extra=0) ----
  function detectPrefix() {
    const el = document.querySelector('input[id$="-TOTAL_FORMS"]');
    if (!el) return null;
    return el.id.replace(/^id_/, "").replace(/-TOTAL_FORMS$/, "");
  }

  const btnAdd = document.getElementById("btn-add-line");
  const tbody = document.querySelector("#lines-table tbody");
  const tmpl = document.getElementById("empty-line-row");
  const prefix = detectPrefix();
  const totalForms = prefix ? document.getElementById(`id_${prefix}-TOTAL_FORMS`) : null;

  if (btnAdd && tbody && tmpl && totalForms) {
    btnAdd.addEventListener("click", function () {
      const idx = parseInt(totalForms.value || "0", 10);
      const html = tmpl.innerHTML.replace(/__prefix__/g, String(idx));
      tbody.insertAdjacentHTML("beforeend", html);
      totalForms.value = String(idx + 1);
    });
  }

  function autoGrowTextarea(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
    }

    // grow saat user ngetik
    document.addEventListener("input", function (e) {
    if (e.target && e.target.classList.contains("auto-grow")) {
        autoGrowTextarea(e.target);
    }
    });

    // grow saat halaman load (value sudah ada)
    document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("textarea.auto-grow").forEach(autoGrowTextarea);
    });

    

});


(function () {
  const currencyEl = document.getElementById("id_currency");
  const rateEl = document.getElementById("id_idr_rate");

  if (!currencyEl || !rateEl) return;

  const DEFAULT_RATE = "1,00";   // tampilan Indonesia
  const DEFAULT_CURRENCY_ID = "1"; // ✅ IDR (sesuaikan kalau beda)

  async function fetchLatestRate(currencyId) {
    if (!currencyId || currencyId === DEFAULT_CURRENCY_ID) {
      return DEFAULT_RATE;
    }

    try {
      const res = await fetch(
        `/api/exchange-rate/latest/?currency_id=${currencyId}`,
        { headers: { "X-Requested-With": "XMLHttpRequest" } }
      );
      if (!res.ok) return DEFAULT_RATE;

      const json = await res.json();
      return json.rate || json.rate_to_idr || DEFAULT_RATE;
    } catch (e) {
      console.warn("FX fetch failed:", e);
      return DEFAULT_RATE;
    }
  }

  async function applyRate() {
    // jangan override kalau user sudah edit manual
    if (rateEl.dataset.touched === "1") return;

    const rate = await fetchLatestRate(currencyEl.value);
    rateEl.value = rate;

    // trigger recalculation kalau ada listener lain
    rateEl.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // tandai kalau user edit manual
  rateEl.addEventListener("input", function () {
    rateEl.dataset.touched = "1";
  });

  // ganti currency → auto ambil rate
  currencyEl.addEventListener("change", function () {
    applyRate();
  });

  // initial load
  document.addEventListener("DOMContentLoaded", function () {
    if (!currencyEl.value) {
      currencyEl.value = DEFAULT_CURRENCY_ID;
    }
    applyRate();
  });
})();
