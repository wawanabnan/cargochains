// static/vendor_bookings/vb_queries.js
(function () {
  window.VBQ = window.VBQ || {};

  // ambil booking_group dari header
  VBQ.getBookingGroup = function () {
    const el = document.getElementById("id_booking_group");
   

    return el ? String(el.value || "").trim().toUpperCase() : "";
  };

  // list cost types by group dari VB.costTypes
  VBQ.costTypesByGroup = function (group) {
    group = String(group || "").trim().toUpperCase();
    const list = window.VB && Array.isArray(VB.costTypes) ? VB.costTypes : [];
    return list.filter((x) => x && String(x.cost_group || "").toUpperCase() === group);
  };

  // isi dropdown <select> berdasarkan group
  // return {mode: "none"|"auto"|"pick", pickedId: "..."}
  VBQ.fillCostTypeSelect = function (selectEl, wrapEl, hintEl, group, currentId) {
    if (!selectEl || !wrapEl) return { mode: "none", pickedId: "" };

    const candidates = VBQ.costTypesByGroup(group);
    selectEl.innerHTML = "";

    if (!group) {
      wrapEl.classList.add("d-none");
      if (hintEl) hintEl.textContent = "Pilih Booking Type dulu.";
      return { mode: "none", pickedId: "" };
    }

    if (candidates.length === 0) {
      wrapEl.classList.add("d-none");
      if (hintEl) hintEl.textContent = "";
      if (candidates.length === 1) return { mode: "auto", pickedId: String(candidates[0].id) };
      return { mode: "none", pickedId: "" };
    }

    wrapEl.classList.remove("d-none");
    if (hintEl) hintEl.textContent = `Pilihan sesuai Booking Type: ${String(group).toUpperCase()}`;

    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = "-- pilih cost type --";
    selectEl.appendChild(opt0);

    candidates.forEach((ct) => {
      const opt = document.createElement("option");
      opt.value = String(ct.id);
     // opt.textContent =  '${ct.name}';  //`${ct.name} (${ct.code})`;
        opt.textContent = ct.name;
      selectEl.appendChild(opt);
    });

    selectEl.value = String(currentId || "");
    return { mode: "pick", pickedId: selectEl.value };
  };
})();
