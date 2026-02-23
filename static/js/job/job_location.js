(function (window, $) {

  if (!$ || !$.fn.select2) return;

  function renderItem(item) {
    if (item.loading) return item.text;

    const title = item.text || "";
    const chain = [item.region, item.province].filter(Boolean).join(" — ");
    const sub = item.subtext || "";

    return $(`
      <div>
        <div>
          <strong>${title}</strong>
          ${item.kind ? `<span class="text-muted">[${item.kind}]</span>` : ""}
        </div>
        <div class="text-muted small">${chain || sub}</div>
      </div>
    `);
  }

  function initLocationSelect($el) {

    if ($el.data("select2")) {
      $el.select2("destroy");
    }

    $el.select2({
      width: "100%",
      placeholder: $el.data("placeholder") || "Pilih",
      allowClear: true,
      minimumInputLength: 1,
      ajax: {
        url: $el.data("url"),
        dataType: "json",
        delay: 250,
        data: function (params) {
          return {
            q: params.term || "",
            page: params.page || 1
          };
        },
        processResults: function (data) {
          return {
            results: (data.results || []).map(function (x) {
              return {
                id: x.id,
                text: x.text,
                kind: x.kind || "",
                code: x.code || "",
                subtext: x.subtext || "",
                district: x.district || "",
                region: x.region || "",
                province: x.province || ""
              };
            }),
            pagination: data.pagination || { more: false }
          };
        }
      },
      templateResult: renderItem,
      templateSelection: function (item) {
        return item.text || "";
      }
    });
  }

  function initLocationCopyFeature() {

    const $origin = $("#id_origin");
    const $destination = $("#id_destination");
    const $pickupTextarea = $("#id_pickup");
    const $deliveryTextarea = $("#id_delivery");

    const $chkPickup = $("#id_pickup_from_origin");
    const $chkDelivery = $("#id_delivery_from_destination");

    function formatAddress(loc) {
      const lines = [];
      if (loc.district || loc.text)
        lines.push((loc.district || loc.text).trim());
      if (loc.region)
        lines.push(loc.region.trim());
      if (loc.province)
        lines.push(loc.province.trim());

      return lines.filter(Boolean).join("\n");
    }

    function renderPickupPreview(loc) {
      $("#pickup_district").text(loc.district || loc.text || "-");
      $("#pickup_region").text(loc.region || "-");
      $("#pickup_province").text(loc.province || "-");
    }

    function renderDeliveryPreview(loc) {
      $("#delivery_district").text(loc.district || loc.text || "-");
      $("#delivery_region").text(loc.region || "-");
      $("#delivery_province").text(loc.province || "-");
    }

    function copyOriginToPickup() {
      const data = $origin.select2("data");
      if (!data || !data.length) return;

      const loc = data[0];
      renderPickupPreview(loc);
      if ($pickupTextarea.length)
        $pickupTextarea.val(formatAddress(loc));
    }

    function copyDestinationToDelivery() {
      const data = $destination.select2("data");
      if (!data || !data.length) return;

      const loc = data[0];
      renderDeliveryPreview(loc);
      if ($deliveryTextarea.length)
        $deliveryTextarea.val(formatAddress(loc));
    }

    // CLEAN BINDING
    $chkPickup.off("change").on("change", function () {
      if (this.checked) copyOriginToPickup();
    });

    $chkDelivery.off("change").on("change", function () {
      if (this.checked) copyDestinationToDelivery();
    });

    $origin.off("change").on("change", function () {
      if ($chkPickup.is(":checked")) copyOriginToPickup();
    });

    $destination.off("change").on("change", function () {
      if ($chkDelivery.is(":checked")) copyDestinationToDelivery();
    });

  }

  // PENTING: jalankan setelah DOM ready
  $(function () {
    initLocationCopyFeature();
  });


  $(document).ready(function () {
    $(".js-location-select").each(function () {
      initLocationSelect($(this));
    });
  });

})(window, window.jQuery);