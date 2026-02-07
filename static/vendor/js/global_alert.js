(function () {
  function levelToBs(level) {
    // normalize: django "error" => bootstrap "danger"
    if (level === "error") return "danger";
    if (level === "success") return "success";
    if (level === "warning") return "warning";
    return "info";
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.innerText = String(str ?? "");
    return div.innerHTML;
  }

  // ============== Inline alert ==============
  function showAlert(message, level = "info", opts = {}) {
    const host = document.getElementById("global-alert-host");
    if (!host) return;

    const bsLevel = levelToBs(level);
    const id = `ga_${Math.random().toString(36).slice(2)}`;
    const timeout = opts.timeout ?? 4000;

    const html = `
      <div id="${id}" class="alert alert-${bsLevel} alert-dismissible fade show shadow-sm mb-2" role="alert">
        ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;
    host.insertAdjacentHTML("beforeend", html);

    if (timeout > 0) {
      setTimeout(() => {
        const el = document.getElementById(id);
        if (!el) return;
        const alert = bootstrap.Alert.getOrCreateInstance(el);
        alert.close();
      }, timeout);
    }
  }

  // ============== Toast ==============
  function showToast(message, level = "info", opts = {}) {
    const toastEl = document.getElementById("global-toast");
    const titleEl = document.getElementById("toast-title");
    const bodyEl = document.getElementById("toast-body");
    if (!toastEl || !titleEl || !bodyEl) return;

    const titleMap = { success: "Success", warning: "Warning", error: "Error", info: "Info" };
    titleEl.textContent = opts.title ?? (titleMap[level] || "Notice");
    bodyEl.textContent = message;

    const toast = bootstrap.Toast.getOrCreateInstance(toastEl, {
      delay: opts.delay ?? 4000,
      autohide: opts.autohide ?? true,
    });
    toast.show();
  }

  // ============== Modal alert (blocking) ==============
  function showModal(message, opts = {}) {
    const modalEl = document.getElementById("global-alert-modal");
    const titleEl = document.getElementById("modal-title");
    const bodyEl = document.getElementById("modal-body");
    if (!modalEl || !titleEl || !bodyEl) return;

    titleEl.textContent = opts.title ?? "Alert";
    bodyEl.textContent = message;

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl, { backdrop: "static" });
    modal.show();
  }

  function showConfirm(message, opts = {}) {
    const modalEl = document.getElementById("global-confirm-modal");
    const titleEl = document.getElementById("confirm-title");
    const bodyEl = document.getElementById("confirm-body");
    const okBtn = document.getElementById("confirm-ok");
    const cancelBtn = document.getElementById("confirm-cancel");

    if (!modalEl || !titleEl || !bodyEl || !okBtn || !cancelBtn) {
      return Promise.resolve(false);
    }

    titleEl.textContent = opts.title ?? "Confirm";
    bodyEl.textContent = message;
    okBtn.textContent = opts.okText ?? "OK";
    cancelBtn.textContent = opts.cancelText ?? "Cancel";

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl, {
      backdrop: "static",
      keyboard: false,
    });

    return new Promise((resolve) => {
      let settled = false;

      const cleanup = () => {
        okBtn.removeEventListener("click", onOk);
        cancelBtn.removeEventListener("click", onCancel);
        modalEl.removeEventListener("hidden.bs.modal", onHidden);
      };

      const onOk = () => {
        if (settled) return;
        settled = true;
        cleanup();
        modal.hide();
        resolve(true);
      };

      const onCancel = () => {
        if (settled) return;
        settled = true;
        cleanup();
        modal.hide();
        resolve(false);
      };

      const onHidden = () => {
        // user close via X
        if (settled) return;
        settled = true;
        cleanup();
        resolve(false);
      };

      okBtn.addEventListener("click", onOk);
      cancelBtn.addEventListener("click", onCancel);
      modalEl.addEventListener("hidden.bs.modal", onHidden);

      modal.show();
    });
  }


  // Expose globally
  window.GlobalAlert = { showAlert, showToast, showModal };

  // ============== Auto-consume Django messages ==============
  document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("django-messages");
    if (!container) return;

    const items = container.querySelectorAll("div[data-tags][data-text]");

    items.forEach((el) => {
      const tags = (el.getAttribute("data-tags") || "")
        .split(/\s+/)
        .filter(Boolean);

      const text = el.getAttribute("data-text") || "";

      // level: success | error | warning | info
      const level =
        tags.find((t) => ["success", "error", "warning", "info"].includes(t)) ||
        "info";

      // ui selector
      const ui =
        tags.includes("ui-modal")
          ? "modal"
          : tags.includes("ui-toast")
          ? "toast"
          : tags.includes("ui-inline")
          ? "inline"
          : "inline"; // default

      if (ui === "modal") {
        showModal(text, {
          title:
            level === "success"
              ? "Success"
              : level === "error"
              ? "Error"
              : "Notice",
        });
        return;
      }

      if (ui === "toast") {
        showToast(text, level);
        return;
      }

      // inline alert
      showAlert(text, level, { timeout: 5000 });
    });
  });
  
  //================ End of Auto-consume Django meesafes=======
})();


//messages.success(request, "Quotation berhasil dibuat.", extra_tags="ui-modal")
//messages.success(request, "Draft disimpan.", extra_tags="ui-toast")
//messages.warning(request, "Tanggal mepet.", extra_tags="ui-inline")
//messages.error(request, "Gagal simpan data.", extra_tags="ui-modal")
