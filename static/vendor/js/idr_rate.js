document.addEventListener("DOMContentLoaded", function () {
  const currencyEl = document.getElementById("id_currency");
  const rateEl = document.getElementById("id_idr_rate");

  if (!currencyEl || !rateEl) {
    console.warn("FX: currency or rate input not found");
    return;
  }

  const DEFAULT_CURRENCY_ID = "1"; // IDR
  const DEFAULT_RATE = "1";

  const DISPLAY_DECIMALS = 3; // tampil 3 digit
  const RAW_DECIMALS = 6;     // simpan 6 digit utk backend (idr_rate decimal_places=6)

  function parseFlexible(val) {
    const s = String(val ?? "").trim();
    if (!s) return NaN;

    // kalau ada koma -> format Indonesia (1.000,25)
    if (s.includes(",")) {
      const normalized = s.replace(/\./g, "").replace(",", ".");
      const n = Number(normalized);
      return Number.isFinite(n) ? n : NaN;
    }

    // selain itu -> dot decimal biasa (1000.250000)
    const n = Number(s.replace(/,/g, ""));
    return Number.isFinite(n) ? n : NaN;
  }

  function formatId(num) {
    return new Intl.NumberFormat("id-ID", {
      minimumFractionDigits: DISPLAY_DECIMALS,
      maximumFractionDigits: DISPLAY_DECIMALS,
    }).format(num);
  }

  function setDisplayAndRaw(num) {
    if (!Number.isFinite(num)) return;
    // simpan raw utk submit (dot-decimal)
    rateEl.dataset.raw = num.toFixed(RAW_DECIMALS);
    // tampilkan format Indonesia 3 digit
    rateEl.value = formatId(num);
  }

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
    const n = parseFlexible(rate);
    if (Number.isFinite(n)) {
      setDisplayAndRaw(n);
    } else {
      // fallback: tetap set apa adanya
      rateEl.value = rate;
      delete rateEl.dataset.raw;
    }
  }

  // user edit manual
  rateEl.addEventListener("input", function () {
    rateEl.dataset.touched = "1";
  });

  // format ulang saat user selesai edit (blur)
  rateEl.addEventListener("blur", function () {
    const n = parseFlexible(rateEl.value);
    if (Number.isFinite(n)) setDisplayAndRaw(n);
  });

  // currency change
  currencyEl.addEventListener("change", function () {
    console.log("FX: currency changed to", currencyEl.value);
    applyRate();
  });

  // sebelum submit: kirim raw (dot-decimal) ke backend
  const form = rateEl.closest("form");
  if (form) {
    form.addEventListener("submit", function () {
      if (rateEl.dataset.raw) {
        rateEl.value = rateEl.dataset.raw; // contoh: 1000.250000
      } else {
        const n = parseFlexible(rateEl.value);
        if (Number.isFinite(n)) rateEl.value = n.toFixed(RAW_DECIMALS);
      }
    });
  }

  // initial load
  if (!currencyEl.value) {
    currencyEl.value = DEFAULT_CURRENCY_ID;
  }

  // kalau field sudah ada nilai dari DB (mis 1.234567), formatkan langsung
  const existing = parseFlexible(rateEl.value);
  if (Number.isFinite(existing)) {
    setDisplayAndRaw(existing);
  } else {
    applyRate();
  }
});
