(function () {

  const container = document.getElementById("attachmentSection");
  if (!container) return;

  const JOB_ID = container.dataset.jobId;

  function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
  }

  // =========================
  // UPLOAD
  // =========================
  const uploadBtn = document.getElementById("uploadBtn");

  if (uploadBtn) {
    uploadBtn.addEventListener("click", function () {

      const fileInput = document.querySelector("#id_file");
      const descInput = document.querySelector("#id_description");

      if (!fileInput.files.length) {
        alert("Pilih file dulu om.");
        return;
      }

      const formData = new FormData();
      formData.append("file", fileInput.files[0]);
      formData.append("description", descInput.value);

      fetch(`/job/${JOB_ID}/attachment/add/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCSRFToken()
        },
        body: formData
      })
      .then(res => res.json())
      .then(data => {

        if (!data.success) {
          alert("Upload gagal.");
          return;
        }

        const tbody = document.querySelector("#attachmentTable tbody");

        const row = document.createElement("tr");
        row.setAttribute("data-id", data.id);

        row.innerHTML = `
          <td><a href="${data.file_url}" target="_blank">${data.filename}</a></td>
          <td>${data.description || "-"}</td>
          <td>${data.created}</td>
          <td>${data.uploaded_by}</td>
          <td class="text-end">
            <button type="button"
                    class="btn btn-outline-danger btn-xs delete-attachment"
                    data-id="${data.id}">
              <i class="fa fa-trash"></i>
            </button>
          </td>
        `;

        tbody.appendChild(row);

        fileInput.value = "";
        descInput.value = "";

      })
      .catch(() => alert("Terjadi error upload."));

    });
  }

  // =========================
  // DELETE
  // =========================
  document.addEventListener("click", function (e) {

    const btn = e.target.closest(".delete-attachment");
    if (!btn) return;

    if (!confirm("Hapus file ini?")) return;

    const attId = btn.dataset.id;

    fetch(`/job/${JOB_ID}/attachment/${attId}/delete/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCSRFToken()
      }
    })
    .then(res => res.json())
    .then(data => {
      if (!data.success) return;

      const row = document.querySelector(`tr[data-id="${attId}"]`);
      if (row) row.remove();
    })
    .catch(() => alert("Terjadi error delete."));

  });

})();