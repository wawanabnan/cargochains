// static/js/location_autocomplete.js
(function($) {
  window.initLocationAutocomplete = function(textSelector, hiddenSelector) {
    const $text = $(textSelector);
    const $hidden = $(hiddenSelector);

    if (!$text.length || !$hidden.length) {
      console.warn("LocationAutocomplete: selector tidak ketemu:", textSelector, hiddenSelector);
      return;
    }

    const url = $text.data('url') || '/geo/locations/autocomplete/';

    $text.autocomplete({
      minLength: 1,
      delay: 150,
      appendTo: 'body',
      position: { my: 'left top+4', at: 'left bottom' },
      source: (req, resp) => {
        $.getJSON(url, { q: req.term })
          .done(data => resp($.map(data || [], o => ({
            label: o.name,
            value: o.name,
            id: o.id,
            name: o.name,
            kind: (o.kind || '').replace(/^./, c => c.toUpperCase())
          }))))
          .fail(() => resp([]));
      },
      select: (e, ui) => {
        $text.val(ui.item.value);
        $hidden.val(ui.item.id).trigger('change');
        return false;
      },
      change: (e, ui) => {
        if (!ui || !ui.item) {
          $hidden.val('').trigger('change');
        }
      },
      focus: () => false
    });

    // OPTIONAL: kalau mau name kiri, kind kanan:
    const ac = $text.autocomplete("instance");
    if (ac) {
      ac._renderItem = function(ul, item) {
        return $("<li>")
          .append(
            $("<div>").addClass("d-flex justify-content-between")
              .append($("<span>").text(item.name))
              .append($("<span>").addClass("text-muted ms-2").text(item.kind))
          )
          .appendTo(ul);
      };
    }
  };
})(jQuery);
