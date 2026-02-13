function initLocationSelect2($el, url) {
  $el.select2({
    width: "100%",
    ajax: {
      url: url,
      dataType: "json",
      delay: 250,
      data: (params) => ({ q: params.term || "" }),
      processResults: (data) => {
        const results = (data || []).map(item => ({
          id: item.id,
          text: item.label,
          district: item.district,
          region: item.region,
          province: item.province
        }));
        return { results };
      },
    },
  });
}
