// Ilovani ishga tushirish: ekran xaritasi va boshlang'ich yuklash.
//
// MUHIM: bu fayl ENG OXIRIDA yuklanishi SHART — quyidagi xarita barcha
// ekran funksiyalariga havola qiladi, ular esa o'z fayllarida aniqlanadi.
// Agar bu fayl oldinroq yuklansa, funksiyalar hali mavjud bo'lmaydi.
const EKRAN_YUKLOVCHILAR = {
  bosh_sahifa: boshSahifaniYuklash,
  portfel: portfelniYuklash,
  mijozlar: mijozlarBazasiniYuklash,
  talabnoma: talabnomaniYuklash,
  davo_ariza: davoArizaniYuklash,
  biznes_hamroh: biznesHamrohniYuklash,
  sud: sudIshlariniYuklash,
  mib: mibIjroniYuklash,
  sugurta_undirish: sugurtaUndirishniYuklash,
  chora: choraKorishniYuklash,
  '95413': nazorat95413niYuklash,
  tahlil: tahlilniYuklash,
  vafot: vafotEtganlarniYuklash,
  reja_grafik: rejaGrafikniYuklash,
  sozlamalar: umumiySozlamalarniYuklash,
};
