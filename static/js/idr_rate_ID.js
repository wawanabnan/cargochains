document.addEventListener("DOMContentLoaded", function () {

  const currencyEl = document.getElementById("id_currency");
  const rateEl = document.getElementById("id_idr_rate");

  if (!currencyEl || !rateEl) return;

  const DEFAULT_CURRENCY_ID = "1"; // IDR
  const DEFAULT_RATE = 1;

  function formatID(n) {
    n = Number(n || 0);
    return n.toLocaleString("id-ID", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    });
  }

  function parseID(val) {
    if (!val) return 0;
    return parseFloat(
      String(val)
        .replace(/\./g, "")
        .replace(",", ".")
    ) || 0;
  }

  async function fetchLatestRate(currencyId) {
    if (!currencyId || currencyId === DEFAULT_CURRENCY_ID) {
      return DEFAULT_RATE;
    }

    try {
      const res = await fetch(`/api/exchange-rate/latest/?currency_id=${currencyId}`, {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      if (!res.ok) return DEFAULT_RATE;

      const json = await res.json();
      return parseFloat(json.rate || json.rate_to_idr || DEFAULT_RATE);

    } catch (err) {
      console.error("FX fetch error:", err);
      return DEFAULT_RATE;
    }
  }

  async function applyRate() {
    const rate = await fetchLatestRate(currencyEl.value);
    rateEl.value = formatID(rate);
  }

  // Currency change
  currencyEl.addEventListener("change", applyRate);

  // Initial load
  if (!currencyEl.value) {
    currencyEl.value = DEFAULT_CURRENCY_ID;
  }

  applyRate();

  // 🔥 BEFORE SUBMIT → convert ke format backend (1000.00)
  const form = rateEl.closest("form");
  if (form) {
    form.addEventListener("submit", function () {
      const numeric = parseID(rateEl.value);
      rateEl.value = numeric.toFixed(4);
    });
  }

});