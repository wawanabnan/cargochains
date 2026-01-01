// jobcost_ajax.js (CLEAN)
// - AJAX submit untuk Job Cost formset
// - Replace partial HTML ke container
// - Re-init JS table via window.initJobCostTable()
// - Handle 400: tetap render html + fokus field error pertama (worksheet style)

(function () {
  "use strict";

  const FORM_ID = "jobcost-form";
  const ALERT_ID = "jobcost-alert";
  const DEBUG_ID = "jobcost-debug";

  // container utama: prefer jobcost-area, fallback jobcost-container
  function getRoot() {
    return (
      document.getElementById("jobcost-area") ||
      document.getElementById("jobcost-container") ||
      document
    );
  }

  function $(id) {
    return document.getElementById(id);
  }

  function getCSRFToken(form) {
    const el = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return el ? el.value : "";
  }

  // ---- alert helper ----
  let jobcostAlertTimer = null;
  const JOBCOST_ALERT_ENABLED = true;

  function showJobCostAlert(msg, type, autoHideMs = 0) {
    if (!JOBCOST_ALERT_ENABLED) return;
    const el = $(ALERT_ID);
    if (!el) return;

    el.classList.remove(
      "d-none",
      "alert-info",
      "alert-success",
      "alert-danger",
      "alert-warning"
    );
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

  // ---- debug helper (optional) ----
  function dumpJobCostDebug(payload) {
    const params = new URLSearchParams(window.location.search);
    if (params.get("debug") !== "1") return; // ⬅️ kunci utama

    const el = document.getElementById("jobcost-debug");
    if (!el) return;

    el.classList.remove("d-none");
    el.textContent = JSON.stringify(payload, null, 2);
  }


  // ---- reveal invalid fields inside hidden wrappers ----
  function revealInvalidJobCostFields(root) {
    if (!root) return;

    root.querySelectorAll(".js-vendor-wrap, .js-internal-note-wrap").forEach((wrap) => {
      if (wrap.querySelector(".is-invalid, [aria-invalid='true']")) {
        wrap.classList.remove("d-none");
      }
    });
  }

  // ---- focus invalid first field ----
  function focusFirstJobCostError(root) {
    root = root || document;

    // prioritas input/textarea dulu (worksheet), lalu select
    const el =
      root.querySelector("input.is-invalid, textarea.is-invalid") ||
      root.querySelector("select.is-invalid") ||
      root.querySelector('[aria-invalid="true"]');

    if (!el) return;

    setTimeout(() => {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.focus();
    }, 30);
  }

  // ---- response reader (aman untuk 400/HTML/empty body) ----
  async function readResponse(resp) {
    const text = await resp.text();
    const contentType = resp.headers.get("content-type") || "";

    let data = null;

    if (text) {
      try {
        data = JSON.parse(text);
      } catch (e) {
        data = { ok: false, message: "Response bukan JSON", rawText: text };
      }
    }

    if (!resp.ok) {
      return { __http_error: true, status: resp.status, contentType, ...(data || {}) };
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

    dumpJobCostDebug({
      ts: new Date().toISOString(),
      phase: data && data.__http_error ? "error" : "success",
      http: {
        status: resp.status,
        ok: resp.ok,
        contentType: resp.headers.get("content-type") || "",
      },
      data,
    });

    // replace partial (baik success maupun error)
    if (data && data.html) {
      const root = getRoot();
      // kalau root = document, jangan innerHTML (safety)
      if (root !== document) root.innerHTML = data.html;

      if (typeof window.initJobCostTable === "function") {
        window.initJobCostTable();
      }
    }

    // INVALID 400 => alert + buka wrapper hidden + fokus
    if (data && data.__http_error) {
      showJobCostAlert(
        data.message || "Ada error input. Cek field yang disorot.",
        "danger",
        0
      );

      const root = getRoot();
      revealInvalidJobCostFields(root);
      focusFirstJobCostError(root);

      return data;
    }

    // SUCCESS
    showJobCostAlert(data?.message || "Tersimpan ✅", "success", 2500);
    return data;
  }

  // ---- bind once ----
  function bindOnce() {
    const form = $(FORM_ID);
    if (!form) return;

    if (form.dataset.jobcostAjaxBound === "1") return;
    form.dataset.jobcostAjaxBound = "1";

    // touched tracker (optional)
    const touched = document.getElementById("jobcost-touched");
    const root = getRoot();
    const container = root !== document ? root : form;

    if (touched && container) {
      const markTouched = () => (touched.value = "1");

      container.addEventListener("input", markTouched, true);
      container.addEventListener("change", markTouched, true);

      container.addEventListener(
        "click",
        (ev) => {
          const t = ev.target;
          if (!t) return;
          if (
            t.closest(".remove-row") ||
            t.closest(".add-row") ||
            t.closest("#btn-jobcost-add")
          ) {
            markTouched();
          }
        },
        true
      );
    }

    form.addEventListener("submit", (ev) => {
      ev.preventDefault();

      const submitBtn =
        form.querySelector('button[type="submit"]') ||
        form.querySelector('input[type="submit"]');

      if (submitBtn) submitBtn.disabled = true;

      submitJobCostAjax(form)
        .catch((err) => {
          console.error("AJAX runtime error:", err);

          dumpJobCostDebug({
            ts: new Date().toISOString(),
            phase: "runtime_error",
            message: err?.message || String(err),
          });

          showJobCostAlert("Gagal simpan (network/runtime error).", "danger", 0);
        })
        .finally(() => {
          if (submitBtn) submitBtn.disabled = false;
        });
    });
  }

  (function enableJobCostDebug() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("debug") !== "1") return;

    const el = document.getElementById("jobcost-debug");
    if (!el) return;

    el.classList.remove("d-none");
  })();

  document.addEventListener("DOMContentLoaded", bindOnce);
})();
