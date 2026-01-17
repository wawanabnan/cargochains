document.addEventListener("DOMContentLoaded", function () {
  const currencyEl = document.getElementById("id_currency");
  const rateEl = document.getElementById("id_idr_rate");

  if (!currencyEl || !rateEl) {
    console.warn("FX: currency or rate input not found");
    return;
  }

  const DEFAULT_CURRENCY_ID = "1"; // IDR
  const DEFAULT_RATE = "1";

  async function fetchLatestRate(currencyId) {
    if (!currencyId || currencyId === DEFAULT_CURRENCY_ID) {
      return DEFAULT_RATE;
    }

    const url = `/api/exchange-rate/latest/?currency_id=${encodeURIComponent(currencyId)}`;

    try {
      const res = await fetch(url, {
         credentials: "same-origin",  
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      if (!res.ok) {
        console.warn("FX: bad response", res.status);
        return DEFAULT_RATE;
      }

      const json = await res.json();
      console.log("FX API:", json);
      return json.rate || json.rate_to_idr || DEFAULT_RATE;
    } catch (err) {
      console.error("FX fetch error:", err);
      return DEFAULT_RATE;
    }
  }

  async function applyRate() {
    // kalau user sudah edit manual → jangan override
    if (rateEl.dataset.touched === "1") return;

    const rate = await fetchLatestRate(currencyEl.value);
    rateEl.value = rate;
  }

  // user edit manual
  rateEl.addEventListener("input", function () {
    rateEl.dataset.touched = "1";
  });

  // currency change
  currencyEl.addEventListener("change", function () {
    console.log("FX: currency changed to", currencyEl.value);
    applyRate();
  });

  // initial load
  if (!currencyEl.value) {
    currencyEl.value = DEFAULT_CURRENCY_ID;
  }
  applyRate();
});
