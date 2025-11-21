// static/js/partner_autocomplete.js
(function($) {
  // textSelector: input text autocomplete
  // hiddenSelector: input hidden yang menyimpan ID partner
  // addressSelector (opsional): textarea alamat yang mau diisi otomatis
  window.initPartnerAutocomplete = function(textSelector, hiddenSelector, addressSelector) {
    const $text = $(textSelector);
    const $hidden = $(hiddenSelector);
    const $addr = addressSelector ? $(addressSelector) : null;

    if (!$text.length || !$hidden.length) {
      console.warn("PartnerAutocomplete: selector tidak ketemu:", textSelector, hiddenSelector);
      return;
    }

    const url = $text.data("url") || "/partners/autocomplete/";

    $text.autocomplete({
      minLength: 1,
      delay: 150,
      appendTo: "body",
      position: { my: "left top+4", at: "left bottom" },
      source: function(req, resp) {
        $.getJSON(url, { q: req.term })
          .done(function(data) {
            resp($.map(data || [], function(o) {
              return {
                label: o.label || o.name,
                value: o.value || o.label || o.name,
                id: o.id,
                name: o.name,
                company_name: o.company_name || "",
                address: o.address || "",
                phone: o.phone || "",
                mobile: o.mobile || "",
                province_id: o.province_id || null,
                regency_id: o.regency_id || null,
                district_id: o.district_id || null,
                village_id: o.village_id || null,
              };
            }));
          })
          .fail(function() {
            resp([]);
          });
      },
      select: function(e, ui) {
        $text.val(ui.item.value);
        $hidden.val(ui.item.id).trigger("change");

        if ($addr && ui.item.address) {
          $addr.val(ui.item.address);
        }

        // simpan & broadcast ke listener (misalnya freight form)
        $text.data("selectedPartner", ui.item);
        $text.trigger("partner:selected", ui.item);

        return false;
      },
      change: function(e, ui) {
        if (!ui || !ui.item) {
          $hidden.val("").trigger("change");
          $text.data("selectedPartner", null);
        }
      },
      focus: function() {
        return false;
      }
    });

    // Optional: tampilan suggestion
    const ac = $text.autocomplete("instance");
    if (ac) {
      ac._renderItem = function(ul, item) {
        const main = item.company_name || item.name;
        const sub = item.company_name ? item.name : "";

        const $div = $("<div>").addClass("d-flex flex-column");
        $div.append($("<span>").text(main));
        if (sub) {
          $div.append($("<small>").addClass("text-muted").text(sub));
        }

        return $("<li>").append($div).appendTo(ul);
      };
    }
  };
})(jQuery);
