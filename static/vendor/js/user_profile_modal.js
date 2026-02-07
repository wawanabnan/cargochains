(function () {
function qs(sel, root) { return (root || document).querySelector(sel); }

const ProfileModal = {
    init() {
    this.btnOpen = qs("#btn-open-profile-modal");
    this.modalEl = qs("#profileModal");
    this.modalBody = qs("#profileModalBody");

    if (!this.btnOpen || !this.modalEl || !this.modalBody) return;

    this.btnOpen.addEventListener("click", () => this.loadForm());
    // optional: kalau kamu buka modal dari tempat lain, bisa hook event 'shown.bs.modal'
    },

    async loadForm() {
    const url = this.btnOpen.getAttribute("data-profile-url");
    this.modalBody.innerHTML = '<div class="text-secondary small">Loading...</div>';

    try {
        const resp = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
        this.modalBody.innerHTML = await resp.text();
        this.bindForm();
    } catch (e) {
        this.modalBody.innerHTML = '<div class="text-danger small">Failed to load profile form.</div>';
        console.log(e);
    }
    },

    bindForm() {
    const form = qs("#profileModalForm", this.modalBody);
    if (!form) return;

    // bind submit (hindari double-binding)
    form.addEventListener("submit", (e) => this.submit(e), { once: true });

    // bind preview on file change
    const fileInput = qs("#id_signature", form);
    if (fileInput) {
        fileInput.addEventListener("change", (e) => this.previewFile(e), { once: false });
    }
    },

    previewFile(e) {
    const input = e.target;
    if (!input.files || !input.files[0]) return;

    const img = qs("#signaturePreviewImg", this.modalBody);
    const empty = qs("#signaturePreviewEmpty", this.modalBody);

    const url = URL.createObjectURL(input.files[0]);
    if (img) {
        img.src = url;
        img.style.display = "";
    }
    if (empty) empty.style.display = "none";
    },

    async submit(e) {
    e.preventDefault();

    const form = e.target;
    const btnSave = qs("#btn-profile-save", this.modalBody);
    const hint = qs("#profile-saving-hint", this.modalBody);

    btnSave && (btnSave.disabled = true);
    hint && hint.classList.remove("d-none");

    try {
        const resp = await fetch(form.getAttribute("action"), {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: new FormData(form),
        });

        const data = await resp.json().catch(() => ({}));

        btnSave && (btnSave.disabled = false);
        hint && hint.classList.add("d-none");

        if (!resp.ok || !data.ok) {
        // server return html form with errors → render ulang + bind ulang
        if (data.html) {
            this.modalBody.innerHTML = data.html;
            this.bindForm();
            return;
        }
        alert(data.message || "Save failed");
        return;
        }

        // sukses: update header name + preview signature dari server
        this.updateHeaderName(data);
        this.updateSignaturePreview(data);

        this.toast("Profile updated");

        // pilihan UX:
        // - kalau mau tetap buka modal supaya user lihat preview: DO NOTHING
        // - kalau mau tutup modal:
        // this.hideModal();

    } catch (err) {
        btnSave && (btnSave.disabled = false);
        hint && hint.classList.add("d-none");
        alert("Save failed (server/network)");
        console.log(err);
    }
    },

    updateHeaderName(data) {
    const nameEl = qs(".dropdown-header");
    if (!nameEl) return;

    // pakai dari response kalau ada; kalau tidak, fallback baca dari input
    const display = (data && data.display_name) ? data.display_name : null;
    if (display) {
        nameEl.textContent = display;
        return;
    }

    const first = qs("#id_first_name", this.modalBody)?.value || "";
    const last = qs("#id_last_name", this.modalBody)?.value || "";
    const username = qs("#id_username", this.modalBody)?.value || "";
    const full = (first + " " + last).trim();
    nameEl.textContent = full || username;
    },

    updateSignaturePreview(data) {
    if (!data || typeof data.signature_url === "undefined") return;

    const img = qs("#signaturePreviewImg", this.modalBody);
    const empty = qs("#signaturePreviewEmpty", this.modalBody);

    if (data.signature_url) {
        const busted = data.signature_url + (data.signature_url.includes("?") ? "&" : "?") + "v=" + Date.now();
        if (img) {
        img.src = busted;
        img.style.display = "";
        }
        if (empty) empty.style.display = "none";
    }
    },

    hideModal() {
    if (!window.bootstrap) return;
    const modal = window.bootstrap.Modal.getInstance(this.modalEl);
    modal && modal.hide();
    },

    toast(msg) {
    const wrap = document.createElement("div");
    wrap.className = "position-fixed bottom-0 end-0 p-3";
    wrap.style.zIndex = 1080;
    wrap.innerHTML = `
        <div class="alert alert-success shadow-sm mb-0 py-2 px-3">
        ${msg}
        </div>
    `;
    document.body.appendChild(wrap);
    setTimeout(() => wrap.remove(), 1800);
    },
};

document.addEventListener("DOMContentLoaded", function () {
    ProfileModal.init();
    window.ProfileModal = ProfileModal; // optional buat debug
});
})();


    