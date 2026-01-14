(function () {
  function initModalDatepicker() {
    if (typeof flatpickr === "undefined") return;

    const modal = document.getElementById("vbDetailModal");
    if (!modal) return;

    // init semua input tanggal di modal
    modal.querySelectorAll("input.vb-date").forEach((el) => {
      if (el._vbFp) return; // prevent double init

      el._vbFp = flatpickr(el, {
        dateFormat: "d/m/Y",     // tampil dd/mm/yyyy
        allowInput: true,
        clickOpens: true,
        // auto-open saat fokus (ini yang om mau)
        onReady: function (_, __, fp) {
          el.addEventListener("focus", function () {
            fp.open();
          });
        },
      });
    });
  }

  // init saat DOM ready
  document.addEventListener("DOMContentLoaded", initModalDatepicker);

  // init ulang setiap kali modal dibuka (kalau modal content dinamis)
  document.addEventListener("shown.bs.modal", function (e) {
    if (e.target && e.target.id === "vbDetailModal") {
      initModalDatepicker();
    }
  });

  // helper convert jika nanti om mau simpan ISO:
  // dd/mm/yyyy -> yyyy-mm-dd
  window.VB = window.VB || {};
  VB.ddmmyyyy_to_iso = function (s) {
    if (!s) return "";
    const m = String(s).trim().match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (!m) return "";
    return `${m[3]}-${m[2]}-${m[1]}`;
  };

  // yyyy-mm-dd -> dd/mm/yyyy (buat load dari JSON iso)
  VB.iso_to_ddmmyyyy = function (s) {
    if (!s) return "";
    const m = String(s).trim().match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!m) return "";
    return `${m[3]}/${m[2]}/${m[1]}`;
  };
})();
