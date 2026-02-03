document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("input[data-flatpickr='date']").forEach((el) => {
    flatpickr(el, {
      dateFormat: "Y-m-d",
      altInput: true,
      altFormat: "d-m-Y",
      allowInput: true
    });
  });
});
