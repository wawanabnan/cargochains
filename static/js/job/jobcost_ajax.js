// jobcost_ajax.js
// AJAX submit khusus untuk Job Cost formset.
// - Mengirim POST via fetch (AJAX)
// - Selalu menampung response/error ke <pre id="jobcost-debug"> (kalau ada)
// - Replace partial HTML ke #jobcost-container (kalau server kirim {html: "..."} )
// - Re-init JS table via window.initJobCostTable() (kalau ada)

(function () {
  "use strict";

  const FORM_ID = "jobcost-form";
  const CONTAINER_ID = "jobcost-container";
  const ALERT_ID = "jobcost-alert";
  const DEBUG_ID = "jobcost-debug";

  // Boleh dimatikan di production kalau mau
  const JOBCOST_ALERT_ENABLED = true;

  // ---- helpers ----
  function $(id) {
    return document.getElementById(id);
  }

  function getCSRFToken(form) {
    const el = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return el ? el.value : "";
  }

  // ---- alert helper (SUPPORT autoHideMs) ----
  let jobcostAlertTimer = null;

  function showJobCostAlert(msg, type, autoHideMs = 0) {
    if (!JOBCOST_ALERT_ENABLED) return;
    const el = $(ALERT_ID);
    if (!el) return;

    el.classList.remove("d-none", "alert-info", "alert-success", "alert-danger", "alert-warning");
    el.classList.add("alert-" + (type || "info"));
    el.textContent = msg || "";

    if (jobcostAlertTimer) clearTimeout(jobcostAlertTimer);
    if (autoHideMs && autoHideMs > 0) {
      jobcostAlertTimer = setTimeout(() => {
        el.classList.add("d-none");
        el.textContent = "";
      }, autoHideMs);
    }
  }

  // ---- debug helper ----
  function dumpJobCostDebug(payload) {
    const el = $(DEBUG_ID);
    if (!el) return; // debug optional

    el.classList.remove("d-none");
    el.textContent = JSON.stringify(payload, null, 2);
  }

  // ---- response reader (AMAN untuk 400/HTML/empty body) ----
  async function readResponse(resp) {
    const text = await resp.text();

    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (e) {
        const err = new Error("Response bukan JSON");
        err.status = resp.status;
        err.rawText = text;
        err.contentType = resp.headers.get("content-type") || "";
        throw err;
      }
    }

    if (!resp.ok) {
      const err = new Error("HTTP Error " + resp.status);
      err.status = resp.status;
      err.data = data;
      err.rawText = text;
      err.contentType = resp.headers.get("content-type") || "";
      throw err;
    }

    return data;
  }

  // ---- main submit ----
  async function submitJobCostAjax(form) {
    const url = form.getAttribute("action") || window.location.href;
    const formData = new FormData(form);

    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCSRFToken(form),
      },
      body: formData,
    });

    const data = await readResponse(resp);

    // dump sukses
    dumpJobCostDebug({
      ts: new Date().toISOString(),
      phase: "success",
      http: {
        status: resp.status,
        ok: resp.ok,
        contentType: resp.headers.get("content-type") || "",
      },
      data: data,
    });

    // replace partial
    if (data && data.html) {
      const container = $(CONTAINER_ID);
      if (container) {
        container.innerHTML = data.html;
      }
      if (typeof window.initJobCostTable === "function") {
        window.initJobCostTable();
      }
    }

  //setupTouchedTracking();


    showJobCostAlert(data?.message || "Tersimpan ✅", "success", 2500);
    return data;
  }




  function setupTouchedTracking() {
    const touched = document.getElementById("jobcost-touched");
    if (!touched) return;

    // observe tempat yang benar-benar berubah saat add/remove row
    const body = document.getElementById("jobcost-body");
    if (!body) return;

    // biar tidak double attach
    if (body.dataset.touchedBound === "1") return;
    body.dataset.touchedBound = "1";

    const markTouched = () => {
      touched.value = "1";
    };

    // edit input/select
    body.addEventListener("input", markTouched, true);
    body.addEventListener("change", markTouched, true);

    // add/remove row = perubahan DOM
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === "childList" && (m.addedNodes.length || m.removedNodes.length)) {
          markTouched();
          break;
        }
      }
    });

    observer.observe(body, { childList: true });
  }


  // ---- bind once ----
  function bindOnce() {

    const touched = document.getElementById("jobcost-touched");
    const container = document.getElementById("jobcost-container") || form;
    //setupTouchedTracking();


    if (touched) {
      const markTouched = () => (touched.value = "1");

      // input/change untuk semua field
      container.addEventListener("input", markTouched, true);
      container.addEventListener("change", markTouched, true);

      // klik add/remove row juga dianggap perubahan
      container.addEventListener("click", (ev) => {
        const t = ev.target;
        if (t && (t.closest(".remove-row") || t.closest(".add-row"))) markTouched();
      }, true);
    }


    const form = $(FORM_ID);
    if (!form) return;

    // guard biar tidak kebinding ulang
    if (form.dataset.jobcostAjaxBound === "1") return;
    form.dataset.jobcostAjaxBound = "1";

    form.addEventListener("submit", (ev) => {
      ev.preventDefault();

      // opsional: disable tombol submit saat saving
      const submitBtn =
        form.querySelector('button[type="submit"]') || form.querySelector('input[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;

      submitJobCostAjax(form)
        .catch((err) => {
          console.error("AJAX save error:", err);

          dumpJobCostDebug({
            ts: new Date().toISOString(),
            phase: "error",
            message: err?.message || String(err),
            status: err?.status || null,
            contentType: err?.contentType || null,
            data: err?.data ?? null,
            rawTextPreview: (err?.rawText || "").slice(0, 2000),
          });

          // tampilkan pesan yang lebih manusiawi
          if (err?.data?.message) {
            showJobCostAlert(err.data.message, "danger", 0);
          } else {
            showJobCostAlert("Gagal simpan (HTTP " + (err?.status || "?") + ")", "danger", 0);
          }

          alert("AJAX error: " + (err?.message || err));
        })
        .finally(() => {
          if (submitBtn) submitBtn.disabled = false;
        });
    });
  }

  document.addEventListener("DOMContentLoaded", bindOnce);
})();
