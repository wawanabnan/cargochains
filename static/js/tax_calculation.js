(function () {

  function parseID(v) {
    if (v === null || v === undefined) return 0;
    let s = String(v).trim();
    if (!s) return 0;
    s = s.replace(/\s+/g, "");
    if (s.includes(",")) {
      s = s.replace(/\./g, "").replace(",", ".");
      const n = Number(s);
      return Number.isFinite(n) ? n : 0;
    }
    const n = Number(s);
    return Number.isFinite(n) ? n : 0;
  }

  function fmtID(n) {
    const x = Number(n || 0);
    return x.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function getCSRFToken() {
    const name = "csrftoken";
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (let c of cookies) {
      c = c.trim();
      if (c.startsWith(name + "=")) return decodeURIComponent(c.slice(name.length + 1));
    }
    return "";
  }

  async function recalcFromBackend() {
    const form = document.querySelector("form");
    if (!form) return;

    const url = form.dataset.taxCalcUrl;
    if (!url) return;

    const qtyEl   = document.getElementById("id_qty");
    const priceEl = document.getElementById("id_price");
    const totalEl = document.getElementById("id_total_amount");
    const taxEl   = document.getElementById("id_tax_amount");
    const pphEl   = document.getElementById("id_pph_amount");
    const grandEl = document.getElementById("id_grand_total");
    const taxesEl = document.getElementById("id_taxes"); // pastikan id ini benar
    const currencyEl = document.getElementById("id_currency");
    const kursEl = document.getElementById("id_kurs_idr");

    if (!qtyEl || !priceEl || !totalEl || !taxEl || !grandEl || !taxesEl) return;

    // hitung total di FE dulu biar responsive
    const qty = parseID(qtyEl.value);
    const price = parseID(priceEl.value);
    const total = qty * price;
    totalEl.value = fmtID(total);

    // ambil selected taxes (multi)
    const taxes = Array.from(taxesEl.selectedOptions || []).map(o => o.value);

    const payload = {
      qty: qty,
      price: price,
      total_amount: total,
      taxes: taxes,
      currency: currencyEl ? currencyEl.value : null,
      kurs_idr: kursEl ? parseID(kursEl.value) : null,
    };

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        console.warn("tax calc failed", res.status);
        return;
      }

      const data = await res.json();

      // backend return angka plain (decimal) → tampilkan format ID
      taxEl.value = fmtID(data.tax_amount || 0);
      if (pphEl) pphEl.value = fmtID(data.pph_amount || 0);
      grandEl.value = fmtID(data.grand_total || 0);

    } catch (e) {
      console.warn("tax calc error", e);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const $ = window.jQuery;
    const taxesEl = document.getElementById("id_taxes");

    // trigger saat select2 berubah
    if ($ && $.fn.select2 && taxesEl) {
      $(taxesEl).on("change", recalcFromBackend);
    } else if (taxesEl) {
      taxesEl.addEventListener("change", recalcFromBackend);
    }

    // juga trigger saat qty/price berubah (biar total + tax ikut update)
    const qtyEl = document.getElementById("id_qty");
    const priceEl = document.getElementById("id_price");
    if (qtyEl) qtyEl.addEventListener("blur", recalcFromBackend);
    if (priceEl) priceEl.addEventListener("blur", recalcFromBackend);

    // initial run
    recalcFromBackend();
  });

})();
