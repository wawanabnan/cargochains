(function (window) {

  function numIDOld(v){
    if(v==null) return 0;
    let s = String(v).trim().replace(/\s+/g,"");
    if(!s) return 0;
    if(s.includes(",")) s = s.replace(/\./g,"").replace(",",".");
    const n = Number(s);
    return Number.isFinite(n) ? n : 0;
  }

  function numargedovID(v){
    if (v == null) return 0;

    let s = String(v).trim();
    if (!s) return 0;

    // hapus semua spasi
    s = s.replace(/\s+/g, "");

    // selalu anggap format Indonesia
    // hapus semua titik ribuan
    s = s.replace(/\./g, "");

    // ganti koma jadi titik desimal
    s = s.replace(",", ".");

    const n = Number(s);
    return Number.isFinite(n) ? n : 0;
    }




  function numID(v) {
    if (v == null) return 0;

    let s = String(v).trim();
    if (!s) return 0;

    // hapus spasi
    s = s.replace(/\s+/g, "");

    // kalau ada koma → berarti format Indonesia
    if (s.includes(",")) {
        // hapus titik ribuan
        s = s.replace(/\./g, "");
        // ganti koma jadi titik desimal
        s = s.replace(",", ".");
    }

    const n = Number(s);
    return Number.isFinite(n) ? n : 0;
}  

  function fmtID(n){
    return new Intl.NumberFormat("id-ID", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(Number(n ?? 0));
  }

  window.JobUtils = {
    numID,
    fmtID
  };

})(window);