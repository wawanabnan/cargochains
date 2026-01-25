console.log("✅✅ idr_kurs.js LOADED / BUILD=20260125-2");

document.addEventListener("DOMContentLoaded", function () {
  const currencyEl = document.getElementById("id_currency");
  const rateEl = document.getElementById("id_idr_rate");

  if (!currencyEl || !rateEl) {
    console.warn("FX: currency or rate input not found");
    return;
  }

  const DEFAULT_CURRENCY_ID = "1"; // IDR
  const DEFAULT_RATE = "1";

  // ---------- helpers ----------
  function normalizeRawMax3(v) {
    let s = String(v ?? "").trim().replace(/\s+/g, "");
    if (!s) return "";

    // allow digit + dot + comma only
    s = s.replace(/[^\d.,]/g, "");

    // indo -> dot decimal
    if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");

    // remove extra dots
    const parts = s.split(".");
    const intPart = parts[0] || "";
    const decPart = (parts[1] || "").slice(0, 3); // ✅ max 3 decimals
    return decPart ? `${intPart}.${decPart}` : intPart;
  }

  function toNumber(raw) {
    const n = Number(raw);
    return Number.isFinite(n) ? n : 0;
  }

  function fmtID3(n) {
    return Number(n || 0).toLocaleString("id-ID", {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3
    });
  }

  function setPrettyFromRaw(raw) {
    const raw3 = normalizeRawMax3(raw);
    rateEl.dataset.raw = raw3;
    rateEl.value = raw3 ? fmtID3(toNumber(raw3)) : "";
  }

  function setRawFromInput() {
    const raw3 = normalizeRawMax3(rateEl.value);
    rateEl.dataset.raw = raw3;
    rateEl.value = raw3; // show raw while editing
  }

  // ---------- API ----------
  async function fetchLatestRate(currencyId) {
    if (!currencyId || currencyId === DEFAULT_CURRENCY_ID) return DEFAULT_RATE;

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
      // prefer json.rate; fallback others
      return json.rate ?? json.rate_to_idr ?? DEFAULT_RATE;
    } catch (err) {
      console.error("FX fetch error:", err);
      return DEFAULT_RATE;
    }
  }

  async function applyRate() {
    // kalau user sudah edit manual → jangan override
    if (rateEl.dataset.touched === "1") return;

    const rate = await fetchLatestRate(currencyEl.value);
    setPrettyFromRaw(rate); // ✅ penting: format 3 desimal setiap apply
  }

  // ---------- user interactions ----------
  rateEl.addEventListener("focus", function () {
    // show raw for editing
    if (rateEl.dataset.raw !== undefined) rateEl.value = rateEl.dataset.raw;
    setTimeout(() => rateEl.select(), 0);
  });

  rateEl.addEventListener("input", function () {
    rateEl.dataset.touched = "1";
    setRawFromInput(); // ✅ limit max 3 decimals realtime
  });

  rateEl.addEventListener("blur", function () {
    // back to pretty
    setPrettyFromRaw(rateEl.dataset.raw ?? rateEl.value);
  });

  currencyEl.addEventListener("change", function () {
    // currency change should reset touched so can auto fetch again
    rateEl.dataset.touched = "0";
    applyRate();
  });

  // before submit => raw decimal
  const form = rateEl.closest("form");
  if (form && !form.dataset.fxSubmitBound) {
    form.dataset.fxSubmitBound = "1";
    form.addEventListener("submit", function () {
      rateEl.value = rateEl.dataset.raw || normalizeRawMax3(rateEl.value) || DEFAULT_RATE;
    }, true);
  }

  // ---------- initial load ----------
  if (!currencyEl.value) currencyEl.value = DEFAULT_CURRENCY_ID;

  // initial: pretty-ize existing value first (server)
  setPrettyFromRaw(rateEl.value || DEFAULT_RATE);

  // then fetch latest if needed
  applyRate();
});
