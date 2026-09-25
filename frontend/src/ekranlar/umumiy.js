// Umumiy yordamchilar — bir necha ekran baravar ishlatadigan
// funksiyalar (dialoglar, fayl yuklash, holat belgilari).
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

function thHisobotJadvalniChizish() {
  const tbody = document.getElementById('th-tbody');
  if (!tbody) return; // Ekran almashtirilgan bo'lsa, jim chiqamiz (xato ko'rsatmaymiz)
  tbody.innerHTML = window._tnHisobotCache.map(r => {
    const checked = window._tnHisobotBelgilangan.has(r.id);
    const holatPill = { yuborildi: 'olib_kelindi', tayyor: 'tayyor', muddati_otgan: 'otgan' }[r.holat] || 'yoq';
    return `<tr>
      <td><span class="checkbox ${checked ? 'checked' : ''}" data-id="${r.id}"></span></td>
      <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.mijoz_turi}</td><td>${r.xat_turi}</td>
      <td>${davoHolatPill(holatPill, r.holat)}</td>
      <td>${(r.yaratilgan_sana || '').slice(0, 10)}</td><td>${(r.yuborilgan_sana || '').slice(0, 10)}</td>
      <td>${r.fayl_yoli ? vafotFaylKnop(r.fayl_yoli, 'Faylni ochish') : '—'}</td>
    </tr>`;
  }).join('');
  tbody.querySelectorAll('.checkbox').forEach(el => {
    el.addEventListener('click', () => {
      const id = parseInt(el.dataset.id, 10);
      if (window._tnHisobotBelgilangan.has(id)) { window._tnHisobotBelgilangan.delete(id); el.classList.remove('checked'); }
      else { window._tnHisobotBelgilangan.add(id); el.classList.add('checked'); }
      const cnt = document.getElementById('th-count');
      if (cnt) cnt.textContent = `Belgilangan: ${window._tnHisobotBelgilangan.size} ta`;
    });
  });
  const cnt = document.getElementById('th-count');
  if (cnt) cnt.textContent = `Belgilangan: ${window._tnHisobotBelgilangan.size} ta`;
}

function davoHolatPill(holat, matn) {
  const klass = { olib_kelindi: 'pill-green', tayyor: 'pill-amber', otgan: 'pill-red', yoq: 'pill-gray' }[holat] || 'pill-gray';
  return `<span class="pill ${klass}">${matn}</span>`;
}

async function davoFileDownloadPost(path, body, filename) {
  const r = await fetch(`${API_BASE}${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  if (!r.ok) { const d = await r.json(); alert('Xato: ' + (d.xato || r.status)); return; }
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

async function tayyorJildYuklabOlish(url) {
  // MUHIM: to'g'ridan-to'g'ri window.open() o'rniga, avval SO'ROVNI o'zimiz
  // yuborib, natija HAQIQIY PDF ekanini tekshiramiz. Aks holda, agar
  // birlashtirishda xato bo'lsa (masalan Windows'da MS Word o'rnatilmagan
  // bo'lsa), foydalanuvchi yangi bo'sh oynada tushunarsiz xom matn (JSON)
  // ko'rar edi va "ishlamayapti" deb o'ylab qolardi — endi aniq xato
  // xabari alert oynasida ko'rsatiladi.
  try {
    const r = await fetch(url);
    const turi = r.headers.get('content-type') || '';
    if (!r.ok || turi.includes('application/json')) {
      const data = await r.json();
      alert('Xato: ' + (data.xato || "Jildni tayyorlashda noma'lum xato yuz berdi."));
      return;
    }
    const blob = await r.blob();
    const nomi = (r.headers.get('content-disposition') || '').match(/filename="?([^"]+)"?/);
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    // Server fayl nomini bermasa — turiga qarab mos nom beramiz
    // (bu funksiya endi Excel hisobotlar uchun ham ishlatiladi).
    const zaxiraNomi = (turi.includes('spreadsheet') || turi.includes('excel')) ? 'hisobot.xlsx'
      : (turi.includes('word') || turi.includes('officedocument.word')) ? 'hujjat.docx' : 'jild.pdf';
    a.download = nomi ? nomi[1] : zaxiraNomi;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(blobUrl);

    // Agar ba'zi hujjatlar jildga qo'shilmagan bo'lsa (masalan skaner fayli
    // buzuq bo'lsa) — jild baribir tayyorlanadi, lekin foydalanuvchi buni
    // BILISHI shart, aks holda to'liqmas jildni sudga olib borib qolardi.
    const ogoh = r.headers.get('X-Jild-Ogohlantirish');
    if (ogoh) {
      alert('Diqqat! Jild tayyor, lekin to\'liq emas.\n\n' + decodeURIComponent(ogoh));
    }
  } catch (e) {
    alert("Jildni yuklab olishda xato: " + e.message);
  }
}

// MUHIM: Excel/PDF hisobotlarni yuklab olish uchun ham aynan shu yo'l
// ishlatiladi. Ilgari bu joylarda `window.open(...)` bor edi — Electronda
// u TASHQI brauzerni ochib yuborardi, va agar ro'yxat bo'sh bo'lsa (server
// {"xato": "..."} qaytarsa), foydalanuvchi brauzerda tushunarsiz xom JSON
// matnni ko'rib, dastur buzilgan deb o'ylardi. Endi xato tushunarli
// oynada ko'rsatiladi, fayl esa to'g'ridan-to'g'ri yuklab olinadi.
function faylniYuklabOlish(url) {
  return tayyorJildYuklabOlish(url);
}

function sudYigmaJildDialogOchish(anketa) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  // MUHIM: iqtisodiy sud ishlarida hujjat nomlari uzunroq ("Davo ariza
  // taraflarga yuborilgani tasdig'i") va yonida sana maydoni ham bo'lgani
  // uchun oyna kengaytirildi — aks holda "Yuklash" tugmalari oyna
  // chetidan chiqib ketib, ko'rinmay qolardi.
  overlay.innerHTML = `<div style="background:#fff;border-radius:12px;padding:20px 24px;width:780px;max-width:94vw;max-height:85vh;overflow-y:auto;" id="syj-modal-content"><div class="loading">Yuklanmoqda...</div></div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', async (e) => {
    if (e.target === overlay) {
      overlay.remove();
      if (typeof sudTopshirishRoyxatniYangilash === 'function' && document.getElementById('sud-tbody')) {
        await sudTopshirishRoyxatniYangilash();
      }
    }
  });
  sudYigmaJildModalniChizish(anketa, overlay);
}

function anketaTarixiDialogOchish(anketa) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `<div style="background:#fff;border-radius:12px;padding:20px 24px;width:700px;max-height:85vh;overflow-y:auto;" id="atarix-content"><div class="loading">Yuklanmoqda...</div></div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

  apiGet(`/anketa/tarix?anketa=${encodeURIComponent(anketa)}`).then(data => {
    const content = overlay.querySelector('#atarix-content');
    content.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <div style="font-size:16px; font-weight:700;">📜 Anketa tarixi — ${anketa}</div>
        <button class="btn" id="atarix-yopish">✕</button>
      </div>
      ${data.tarix.length === 0 ? '<div class="page-sub">Hali hech qanday sikl topilmadi.</div>' : ''}
      ${data.tarix.map((s, i) => `
        <div class="card" style="margin-bottom:10px;">
          <div class="card-h">Sikl №${i + 1} — boshlangan: ${s.yaratilgan_sana}</div>
          <table style="width:100%; font-size:12.5px;">
            <tr><td style="width:110px; color:var(--muted);">Xat</td>
              <td>${s.xat_holati === 'yuborildi' ? '✓ Yuborilgan' : (s.xat_holati || '—')}
                ${s.xat_fayl ? ` &nbsp; <a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(s.xat_fayl)}" target="_blank">📄 Ko'rish</a>` : ''}
              </td></tr>
            <tr><td style="color:var(--muted);">Davo ariza</td>
              <td>${s.davo_ariza_fayl ? '✓ Tayyorlangan' : '—'}
                ${s.davo_ariza_fayl ? ` &nbsp; <a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(s.davo_ariza_fayl)}" target="_blank">📄 Ko'rish</a>` : ''}
              </td></tr>
            <tr><td style="color:var(--muted);">Sud</td>
              <td>${s.sud_ish_raqami ? `Ish №${s.sud_ish_raqami} — ` : ''}${s.sud_natija}
                ${s.sud_yigma_jild_bor ? ` &nbsp; <a href="#" data-anketa-jild="sud-${s.xat_id}">📁 Jildni ko'rish</a>` : ''}
              </td></tr>
            <tr><td style="color:var(--muted);">MIB</td>
              <td>${s.mib_ish_raqami ? `Ish №${s.mib_ish_raqami} — ` : ''}${s.mib_natija}
                ${s.mib_yigma_jild_bor ? ` &nbsp; <a href="#" data-anketa-jild="mib-${s.xat_id}">📁 Jildni ko'rish</a>` : ''}
              </td></tr>
          </table>
        </div>
      `).join('')}
      <div class="card" style="margin-top:12px;">
        <div class="card-h">🗄 Tizimdan oldingi hujjatlar (eski, tartibsiz saqlangan)</div>
        <div class="btn-row">
          <input class="tb-input" id="atarix-eski-q" placeholder="Qidirish (anketa yoki mijoz nomi)" style="width:220px;" value="${anketa}">
          <button class="btn-gold" id="atarix-eski-qidir" style="margin-left:0;">🔍 Qidirish</button>
        </div>
        <div id="atarix-eski-natija" style="margin-top:8px;"></div>
      </div>
    `;
    content.querySelector('#atarix-yopish').addEventListener('click', () => overlay.remove());
    const eskiQidir = async () => {
      const q = content.querySelector('#atarix-eski-q').value.trim();
      const natijaDiv = content.querySelector('#atarix-eski-natija');
      if (!q || q.length < 3) { natijaDiv.innerHTML = '<div class="page-sub">Kamida 3 ta belgi kiriting.</div>'; return; }
      natijaDiv.innerHTML = '<div class="loading">Qidirilmoqda...</div>';
      const res = await fetch(`${API_BASE}/tizimdan_oldin/qidirish?q=${encodeURIComponent(q)}`);
      const d = await res.json();
      if (d.xato) { natijaDiv.innerHTML = `<div class="page-sub" style="color:var(--err);">${d.xato}</div>`; return; }
      if (d.natija.length === 0) { natijaDiv.innerHTML = '<div class="page-sub">Hech narsa topilmadi.</div>'; return; }
      natijaDiv.innerHTML = d.natija.map(f => `
        <div style="font-size:12px; padding:3px 0;">
          📄 <a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(f.toliq_yol)}" target="_blank">${f.fayl_nomi}</a>
          <span style="color:var(--muted);"> — ${f.papka}</span>
        </div>
      `).join('');
    };
    content.querySelector('#atarix-eski-qidir').addEventListener('click', eskiQidir);
    content.querySelectorAll('[data-anketa-jild]').forEach(a => {
      a.addEventListener('click', (e) => {
        e.preventDefault();
        const [turi, xatId] = a.dataset.anketaJild.split('-');
        if (turi === 'sud') sudYigmaJildDialogOchish(anketa);
        // MUHIM: bu yerda ilgari window.open() ishlatilgan edi — Electronda
        // u tashqi brauzerni ochib yuborardi va xato bo'lsa foydalanuvchi
        // tushunarsiz xom JSON matnni ko'rardi. Endi boshqa joylardagi
        // kabi tayyorJildYuklabOlish() ishlatiladi.
        else tayyorJildYuklabOlish(`${API_BASE}/mib/tayyor_jild?anketa=${encodeURIComponent(anketa)}`);
      });
    });
  });
}

// MUHIM: bazadan kelgan matnni (mijoz nomi, izoh, tafsilot) HTML ichiga
// qo'yishdan oldin shu funksiyadan o'tkazish kerak. Sabab: haqiqiy bank
// portfelida yuridik shaxs nomlari qo'shtirnoq bilan yoziladi — masalan
// "GULISTON AGRO" MCHJ. Bunday nom to'g'ridan-to'g'ri qo'yilsa,
// data-mijoz="..." atributi birinchi ichki qo'shtirnoqda UZILIB qoladi va
// tugma noto'g'ri (bo'sh) qiymat bilan ishlaydi; `<` belgisi esa jadval
// qatorining qolgan qismini butunlay yo'q qilib qo'yadi.
function xavfsizMatn(qiymat) {
  if (qiymat === null || qiymat === undefined) return '';
  return String(qiymat)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// MUHIM: Electron (desktop) muhitida brauzerning o'z `prompt()`
// oynasi UMUMAN ISHLAMAYDI — u hech narsa ko'rsatmasdan darhol null
// qaytaradi. Shu sababli "✏ o'zgartirish" tugmalari bosilganda hech
// narsa bo'lmasdi. Quyidagi dialog o'sha vazifani bajaradi va
// dasturning o'z ko'rinishida chiqadi.
//
// Ishlatish:   const yangi = await matnSorash('Sarlavha', 'joriy qiymat');
//              yangi === null bo'lsa — foydalanuvchi bekor qildi.
function matnSorash(sarlavha, joriyQiymat = '', tavsif = '') {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);'
      + 'display:flex;align-items:center;justify-content:center;z-index:1100;';
    overlay.innerHTML = `
      <div style="background:#fff;border-radius:12px;padding:20px 24px;width:460px;max-width:92vw;">
        <div style="font-size:15px;font-weight:700;margin-bottom:6px;">${sarlavha}</div>
        ${tavsif ? `<div class="page-sub" style="margin-bottom:10px;">${tavsif}</div>` : ''}
        <input class="tb-input" id="ms-qiymat" style="width:100%;margin-bottom:14px;">
        <div style="display:flex;justify-content:flex-end;gap:8px;">
          <button class="btn" id="ms-bekor">Bekor qilish</button>
          <button class="btn-gold" id="ms-saqlash" style="margin-left:0;">✓ Saqlash</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    const maydon = overlay.querySelector('#ms-qiymat');
    maydon.value = joriyQiymat == null ? '' : String(joriyQiymat);
    maydon.focus();
    maydon.select();

    const yopish = (natija) => {
      document.removeEventListener('keydown', klavisha);
      overlay.remove();
      resolve(natija);
    };
    const klavisha = (e) => {
      if (e.key === 'Escape') yopish(null);
      if (e.key === 'Enter' && document.activeElement === maydon) yopish(maydon.value);
    };
    document.addEventListener('keydown', klavisha);
    overlay.querySelector('#ms-bekor').addEventListener('click', () => yopish(null));
    overlay.querySelector('#ms-saqlash').addEventListener('click', () => yopish(maydon.value));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) yopish(null); });
  });
}

function mibOverlayOchish(html) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = html;
  document.body.appendChild(overlay);
  return overlay;
}

const AMAL_TURLARI_LABEL = {
  oylik_ish_haqqi: "Oylik ish haqqiga qaratildi", avto_taqiq: "Avto transportga taqiq qo'yildi",
  avto_qidiruv: "Avto transport qidiruvga berildi", chetga_chiqish_taqiq: "Chetga chiqishga taqiq qo'yilgan",
  majburiy_xatlov: "Majburiy xatlov o'tkazildi", sotish_togridan: "To'g'ridan-to'g'ri sotildi",
  sotish_auksion: "Auksion yo'li bilan sotildi", kafil_ish: "Kafil bo'yicha ish qilindi",
  garov_xatlov: "Garov mulkiga xatlov o'tkazildi", garov_sotish: "Garov mulki sotildi",
  eski_ish_kiritildi: "Eski ish sifatida bazaga kiritildi", ish_haqiga_qaratish: "Oylik ish haqqiga qaratildi",
};

function mibNollashDialogOchish(anketa) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:440px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:10px; color:var(--err);">⚠️ Diqqat — qaytarilmaydigan amal</div>
      <div class="page-sub" style="margin:0 0 14px; line-height:1.6;">
        Anketa <b>${anketa}</b> uchun BUTUN xat, Davo ariza, Sud va MIB jarayoni tarixi
        <b>butunlay o'chiriladi</b>. Mijoz "hech qanday harakat qilinmagan" holatiga qaytadi
        va jarayonni noldan (yangi xat yuborishdan) boshlashingiz kerak bo'ladi.<br><br>
        <b>Portfel va to'lovlar tarixi</b> (haqiqiy pul harakati) o'chirilmaydi.<br><br>
        Bu amalni <b>qaytarib bo'lmaydi</b>. Davom etasizmi?
      </div>
      <label style="display:flex; align-items:center; gap:8px; margin-bottom:14px; font-size:13px;">
        <input type="checkbox" id="mn-tasdiq"> Ha, men tushundim va tasdiqlayman
      </label>
      <div style="display:flex; justify-content:flex-end; gap:8px;">
        <button class="btn" id="mn-cancel">Bekor qilish</button>
        <button class="btn danger" id="mn-save">🗑 Butunlay nollashtirish</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  document.getElementById('mn-cancel').addEventListener('click', () => overlay.remove());
  document.getElementById('mn-save').addEventListener('click', async () => {
    if (!document.getElementById('mn-tasdiq').checked) {
      alert("Iltimos, avval tasdiqlash katakchasini belgilang.");
      return;
    }
    const r = await fetch(`${API_BASE}/mib/jarayonni_nollashtirish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anketa_raqami: anketa, tasdiqlayman: true }),
    });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    alert("Jarayon muvaffaqiyatli nollashtirildi. Endi bu mijoz uchun yangidan xat yuborishingiz mumkin.");
    await ekranniOchish('mib');
  });
}

function n95413JadvalniChizish() {
  const bosqichFiltr = document.getElementById('n95-filter').value;
  const turiFiltr = document.getElementById('n95-turi-filter').value;
  let royxat = window._n95Cache;
  if (bosqichFiltr) royxat = royxat.filter(r => r.bosqich === bosqichFiltr);
  if (turiFiltr) royxat = royxat.filter(r => r.turi === turiFiltr);

  const korsatilgan = royxat.slice(0, window._n95KorsatilganSoni);
  document.getElementById('n95-tbody').innerHTML = korsatilgan.map(r => {
    const checked = window._n95Belgilangan.has(r.anketa_raqami);
    return `<tr>
      <td><span class="checkbox ${checked ? 'checked' : ''}" data-anketa="${r.anketa_raqami}"></span></td>
      <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td>
      <td>${formatSum(r.balans_95413)}</td><td>${r.bosqich_nomi}</td><td>${xavfsizMatn(r.tafsilot)}</td>
      <td><a href="#" data-anketa="${r.anketa_raqami}" data-act="f95413-jild">📁 Jild</a></td>
    </tr>`;
  }).join('');
  document.getElementById('n95-tbody').querySelectorAll('[data-act="f95413-jild"]').forEach(a => {
    a.addEventListener('click', (e) => { e.preventDefault(); f95413JildDialogOchish(a.dataset.anketa); });
  });
  document.getElementById('n95-tbody').querySelectorAll('.checkbox').forEach(el => {
    el.addEventListener('click', () => {
      const anketa = el.dataset.anketa;
      if (window._n95Belgilangan.has(anketa)) { window._n95Belgilangan.delete(anketa); el.classList.remove('checked'); }
      else { window._n95Belgilangan.add(anketa); el.classList.add('checked'); }
      document.getElementById('n95-count').textContent = `Belgilangan: ${window._n95Belgilangan.size} ta`;
    });
  });
  document.getElementById('n95-count').textContent = `Belgilangan: ${window._n95Belgilangan.size} ta`;

  const qolgan = royxat.length - window._n95KorsatilganSoni;
  const moreWrap = document.getElementById('n95-more-wrap');
  if (qolgan > 0) {
    moreWrap.innerHTML = `<button class="btn ghost" id="n95-more-btn">⬇ Yana ${Math.min(qolgan, 200)} tasini ko'rsatish (jami ${qolgan} ta qoldi)</button>`;
    document.getElementById('n95-more-btn').addEventListener('click', () => { window._n95KorsatilganSoni += 200; n95413JadvalniChizish(); });
  } else {
    moreWrap.innerHTML = '';
  }
}

async function n95413AmalBajarish() {
  if (window._n95Belgilangan.size !== 1) { alert("Aynan bitta mijozni belgilang (har bir bosqich uchun alohida hujjat kerak)."); return; }
  const anketa = Array.from(window._n95Belgilangan)[0];
  const r = window._n95Cache.find(x => x.anketa_raqami === anketa);
  if (!r) return;

  if (r.bosqich === 'xat_kerak') {
    if (!confirm(`${xavfsizMatn(r.mijoz_nomi)} uchun xat tayyorlansinmi ('Tayyor' holatida saqlanadi)?`)) return;
    const resp = await fetch(`${API_BASE}/talabnoma/xat_yaratish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ anketalar: [anketa] }),
    });
    const data = await resp.json();
    alert(data.yaratildi ? "Xat tayyorlandi ('Tayyor' holatida)." : `Xato: ${data.xatolar.join(', ')}`);
    await ekranniOchish('95413');
  } else if (r.bosqich === 'xat_yuborish_kerak') {
    if (!confirm(`${xavfsizMatn(r.mijoz_nomi)} xati 'Yuborildi' deb belgilansinmi?`)) return;
    // xat_yaratish endpointi mavjud xatni o'tkazib yuboradi, shuning uchun to'g'ridan-to'g'ri
    // 'yuborildi' belgilash uchun Talabnoma hisobotidagi kabi xat ID kerak — buni topamiz:
    const hisobot = await apiGet('/talabnoma/xatlar_hisoboti');
    const xat = hisobot.royxat.find(x => x.anketa_raqami === anketa);
    if (!xat) { alert("Xat topilmadi."); return; }
    await fetch(`${API_BASE}/nazorat95413/xat_yuborildi_belgilash`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ anketa_raqami: anketa }),
    });
    alert("Xat 'Yuborildi' deb belgilandi.");
    await ekranniOchish('95413');
  } else if (r.bosqich === 'davo_ariza_kerak') {
    if (!confirm(`${xavfsizMatn(r.mijoz_nomi)} uchun Davo ariza tayyorlansinmi?`)) return;
    const resp = await fetch(`${API_BASE}/davo-ariza/yaratish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ anketalar: [anketa] }),
    });
    const data = await resp.json();
    alert(data.yaratildi ? "Davo ariza tayyorlandi." : `Xato: ${(data.xatolar || []).join(', ')}`);
    await ekranniOchish('95413');
  } else if (r.bosqich === 'palata_kutilmoqda') {
    n95413OlibKelindiDialog(anketa, r.mijoz_nomi);
  } else if (r.bosqich === 'sud_kerak') {
    n95413SudDialog(anketa, r.mijoz_nomi);
  } else if (r.bosqich === 'mib_kerak') {
    // 95413 oqimida sud_buyrugi holati alohida kuzatilmaydi, shuning uchun
    // xavfsizlik uchun har doim yuklashni so'raymiz (false).
    mibTransferDialog(anketa, false);
    // mibTransferDialog ekranniOchish('mib') bilan yakunlanadi — 95413 uchun qayta yuklaymiz
    setTimeout(() => ekranniOchish('95413'), 500);
  } else if (r.bosqich === 'mib_jarayonida') {
    alert("Bu mijoz allaqachon MIB jarayonida. Ijro harakatlarini qo'shish uchun 'MIB ijro harakatlari' bo'limiga o'ting.");
  }
}

function n95413OlibKelindiDialog(anketa, mijozNomi) {
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:400px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Olib kelindi — ${mijozNomi}</div>
      <label style="display:block;margin-bottom:8px;">Ish raqami<br><input class="tb-input" id="n95-ok-ish" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Sana (kun.oy.yil)<br><input class="tb-input" id="n95-ok-sana" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">SSPdan olib kelingan hujjat skani (PDF) — <b style="color:var(--err);">majburiy</b><br>
        <input type="file" id="n95-ok-skan" accept=".pdf" style="width:100%; margin-top:4px;"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="n95-ok-cancel">Bekor qilish</button>
        <button class="btn-gold" id="n95-ok-save" style="margin-left:0;">✓ Saqlash</button>
      </div>
    </div>`);
  overlay.querySelector('#n95-ok-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#n95-ok-save').addEventListener('click', async () => {
    const ish = overlay.querySelector('#n95-ok-ish').value.trim();
    const sana = overlay.querySelector('#n95-ok-sana').value.trim();
    const skanFile = overlay.querySelector('#n95-ok-skan').files[0];
    if (!ish || !sana) { alert('Ish raqami va sanani kiriting.'); return; }
    if (!skanFile) { alert("SSPdan olib kelingan hujjat skanini (PDF) yuklash majburiy."); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('ish_raqami', ish);
    fd.append('sana', sana);
    fd.append('skan', skanFile);
    const r = await fetch(`${API_BASE}/davo-ariza/olib_kelindi`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    if (data.ogohlantirish) alert(data.ogohlantirish);
    await ekranniOchish('95413');
  });
}

function n95413SudDialog(anketa, mijozNomi) {
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:400px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Sudga topshirildi — ${mijozNomi}</div>
      <label style="display:block;margin-bottom:8px;">Sud ish raqami<br><input class="tb-input" id="n95-sud-ish" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Sana (kun.oy.yil)<br><input class="tb-input" id="n95-sud-sana" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Sud buyrug'i (agar mavjud bo'lsa, PDF)<br>
        <input type="file" id="n95-sud-fayl" accept=".pdf" style="width:100%; margin-top:4px;"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="n95-sud-cancel">Bekor qilish</button>
        <button class="btn-gold" id="n95-sud-save" style="margin-left:0;">✓ Saqlash</button>
      </div>
    </div>`);
  overlay.querySelector('#n95-sud-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#n95-sud-save').addEventListener('click', async () => {
    const ish = overlay.querySelector('#n95-sud-ish').value.trim();
    const sana = overlay.querySelector('#n95-sud-sana').value.trim();
    const fayl = overlay.querySelector('#n95-sud-fayl').files[0];
    if (!ish || !sana) { alert('Ish raqami va sanani kiriting.'); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('ish_raqami', ish);
    fd.append('sana', sana);
    if (fayl) fd.append('sud_buyrugi', fayl);
    const r = await fetch(`${API_BASE}/sud/topshirildi`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    if (data.ogohlantirish) {
      if (!confirm(data.xabar)) return;
      fd.append('majburiy_davom_ettirish', 'true');
      const r2 = await fetch(`${API_BASE}/sud/topshirildi`, { method: 'POST', body: fd });
      const data2 = await r2.json();
      if (data2.xato) { alert('Xato: ' + data2.xato); return; }
    }
    overlay.remove();
    await ekranniOchish('95413');
  });
}

function n95413EskiIshDialogOchish() {
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:420px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:6px;">95413 — Eski ish kiritish</div>
      <div class="page-sub" style="margin:0 0 12px;">Bu dasturdan tashqarida avvalroq MIBga chiqarilgan ish uchun. Yig'ma jild alohida (95413) papkaga yoziladi.</div>
      <label style="display:block;margin-bottom:8px;">Anketa raqami<br>
        <div style="display:flex; gap:6px;">
          <input class="tb-input" id="n95-ei-anketa" style="flex:1;">
          <button class="btn" id="n95-ei-qidirish">🔍 Topish</button>
        </div></label>
      <div id="n95-ei-natija" style="font-size:12.5px; color:var(--muted); margin-bottom:10px;">Hali qidirilmagan</div>
      <label style="display:block;margin-bottom:8px;">MIB ish raqami<br><input class="tb-input" id="n95-ei-ish" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Sud ish raqami (ixtiyoriy)<br><input class="tb-input" id="n95-ei-sud" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">MIBga o'tkazilgan sana<br><input class="tb-input" id="n95-ei-sana" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Hozirgi qarzdorlik (ixtiyoriy)<br><input class="tb-input" id="n95-ei-qarz" style="width:100%;"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="n95-ei-cancel">Bekor qilish</button>
        <button class="btn-gold" id="n95-ei-save" style="margin-left:0;">✓ Kiritish</button>
      </div>
    </div>`);
  overlay.querySelector('#n95-ei-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#n95-ei-qidirish').addEventListener('click', async () => {
    const anketa = overlay.querySelector('#n95-ei-anketa').value.trim();
    if (!anketa) return;
    const data = await apiGet(`/nazorat95413/eski_ish_qidirish?anketa=${encodeURIComponent(anketa)}`);
    overlay.querySelector('#n95-ei-natija').textContent = data.topildi
      ? `Topildi: ${data.mijoz_nomi} (${data.turi}), qarzdorlik: ${formatSum(data.jami_qarz)}, 95413 balansi: ${formatSum(data.balans_95413)}`
      : "Bu anketa portfelda topilmadi.";
  });
  overlay.querySelector('#n95-ei-save').addEventListener('click', async () => {
    const anketa = overlay.querySelector('#n95-ei-anketa').value.trim();
    const ish = overlay.querySelector('#n95-ei-ish').value.trim();
    const sana = overlay.querySelector('#n95-ei-sana').value.trim();
    if (!anketa || !ish || !sana) { alert('Anketa, ish raqami va sanani kiriting.'); return; }
    const r = await fetch(`${API_BASE}/nazorat95413/eski_ish_kiritish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        anketa_raqami: anketa, ish_raqami: ish, sana,
        sud_ish_raqami: overlay.querySelector('#n95-ei-sud').value.trim(),
        qarzdorlik: overlay.querySelector('#n95-ei-qarz').value.trim(),
      }),
    });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    await ekranniOchish('95413');
  });
}

// ---------------- TAHLIL ----------------
// Tahlil bo'limining ochiq bo'limi: portfel yoki huquqiy jarayon

async function thTarmoqMijozlariDialogOchish(tarmoq) {
  const data = await apiGet(`/tahlil/tarmoq_mijozlari?tarmoq=${encodeURIComponent(tarmoq)}`);
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:640px;max-height:80vh;overflow-y:auto;">
      <div style="font-size:16px;font-weight:700;margin-bottom:4px;">${tarmoq}</div>
      <div class="page-sub" style="margin:0 0 12px;">${data.mijozlar.length} ta mijoz (eng yuqori 300 tagacha ko'rsatiladi)</div>
      <table style="width:100%; font-size:12.5px;">
        <thead><tr style="text-align:left; color:var(--muted);"><th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Stage</th><th>EAD</th></tr></thead>
        <tbody>
          ${data.mijozlar.map(m => `<tr>
            <td style="padding:5px 0;">${m.anketa_raqami}</td><td>${xavfsizMatn(m.mijoz_nomi)}</td><td>${m.mijoz_turi}</td>
            <td>${m.stage}</td><td>${formatSum(m.ead)}</td>
          </tr>`).join('')}
        </tbody>
      </table>
      <div style="display:flex; justify-content:flex-end; margin-top:16px;">
        <button class="btn" id="th-tarmoq-yopish">Yopish</button>
      </div>
    </div>`);
  overlay.querySelector('#th-tarmoq-yopish').addEventListener('click', () => overlay.remove());
}

// ---------------- VAFOT ETGANLAR ----------------
function vafotFaylKnop(fayl_yoli, label) {
  if (!fayl_yoli) return `<span style="color:var(--muted); font-size:11.5px;">—</span>`;
  const url = `${API_BASE}/fayl_korish?yol=${encodeURIComponent(fayl_yoli)}`;
  return `<a href="${url}" target="_blank" style="font-size:11.5px;">📄 ${label}</a>`;
}

function mjUstunMoslashtirishDialogOchish(turi, ustunlar, namuna) {
  const maydonlar = [
    ['kalit', "Bog'lovchi ID (STIR / PINFL / Unikal) *", true],
    ['ism', "Ism-familiya / Tashkilot nomi *", true],
    ['manzil', 'Manzil', false],
    ['telefon', 'Telefon', false],
    ['hujjat_raqami', 'Passport / STIR raqami', false],
    ['rahbar_ism', "Rahbar F.I.Sh (yuridik shaxs uchun)", false],
  ];
  const options = ['<option value="">— tanlanmagan —</option>', ...ustunlar.map(c => `<option value="${c}">${c}</option>`)].join('');
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:500px;max-height:80vh;overflow-y:auto;">
      <div style="font-size:16px;font-weight:700;margin-bottom:6px;">Ustunlarni moslashtirish — ${turi === 'jismoniy' ? 'Jismoniy shaxslar' : 'Yuridik shaxslar'}</div>
      <div class="page-sub" style="margin:0 0 14px;">Har bir maydon uchun mos Excel ustunini tanlang.</div>
      ${maydonlar.map(([f, label]) => `
        <div style="margin-bottom:10px;">
          <label style="display:block; font-size:12.5px; color:var(--muted); margin-bottom:4px;">${label}</label>
          <select class="tb-select" id="mj-map-${f}" style="width:100%;">${options}</select>
        </div>`).join('')}
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="mj-map-cancel">Bekor qilish</button>
        <button class="btn-gold" id="mj-map-save" style="margin-left:0;">✓ Import qilish</button>
      </div>
    </div>`);
  overlay.querySelector('#mj-map-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#mj-map-save').addEventListener('click', async () => {
    const mapping = {};
    maydonlar.forEach(([f]) => {
      const v = overlay.querySelector(`#mj-map-${f}`).value;
      if (v) mapping[f] = v;
    });
    if (!mapping.kalit || !mapping.ism) { alert("Bog'lovchi ID va Ism ustunlari majburiy."); return; }
    const r = await fetch(`${API_BASE}/mijozlar/excel_import`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ turi, mapping }),
    });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    alert(`Tayyor! ${data.import_qilingan} / ${data.jami_qator} yozuv import qilindi.`);
    overlay.remove();
    await ekranniOchish('mijozlar');
  });
}

// ---------------- REJA GRAFIK ----------------

async function sudKunlariBoliminiChizish() {
  const body = document.getElementById('reja-body');
  const [royxatData, eslatmalar] = await Promise.all([apiGet('/sud/kunlari'), apiGet('/sud/kunlari/eslatmalar')]);

  let eslatmaHtml = '';
  if (eslatmalar.bugun.length > 0) {
    eslatmaHtml += `<div class="card" style="background:#FEF2F2; border:1px solid #FCA5A5; margin-bottom:10px;">
      <b style="color:var(--err);">⚠ BUGUN SUD BOR:</b> ${eslatmalar.bugun.map(e => `${e.mijoz_nomi} (${e.anketa_raqami}) — soat ${e.sud_vaqti}`).join(', ')}
    </div>`;
  }
  if (eslatmalar.ertaga.length > 0) {
    eslatmaHtml += `<div class="card" style="background:#FEF3C7; border:1px solid #FCD34D; margin-bottom:10px;">
      <b>🔔 ERTAGA SUD BOR:</b> ${eslatmalar.ertaga.map(e => `${e.mijoz_nomi} (${e.anketa_raqami}) — soat ${e.sud_vaqti}`).join(', ')}
    </div>`;
  }

  body.innerHTML = `
    ${eslatmaHtml}
    <div class="card">
      <div class="btn-row">
        <input class="tb-input" id="sk-anketa" placeholder="Anketa raqami" style="width:120px;">
        <input class="tb-input" id="sk-sana" placeholder="Sud sanasi (kun.oy.yil)" style="width:150px;">
        <input class="tb-input" id="sk-vaqt" placeholder="Vaqt (soat:daqiqa)" style="width:110px;">
        <input class="tb-input" id="sk-nomi" placeholder="Sud nomi" style="width:180px;">
        <input class="tb-input" id="sk-ish" placeholder="Sud ish raqami" style="width:130px;">
        <button class="btn-gold" id="sk-qoshish" style="margin-left:0;">+ Qo'shish</button>
        <span style="width:1px; height:22px; background:var(--border); margin:0 2px;"></span>
        <button class="btn" id="sk-excel">📤 Excel orqali yuklash</button>
        <input type="file" id="sk-excel-file" accept=".xlsx,.xls" style="display:none;">
      </div>
    </div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr><th>Anketa №</th><th>Mijoz</th><th>Sud sanasi</th><th>Vaqti</th><th>Sud nomi</th><th>Ish raqami</th><th></th></tr></thead>
          <tbody>
            ${royxatData.royxat.map(r => `<tr>
              <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.sud_sanasi}</td><td>${r.sud_vaqti}</td>
              <td>${r.sud_nomi || '—'}</td><td>${r.sud_ish_raqami || '—'}</td>
              <td><button class="btn danger" data-id="${r.id}" data-act="sk-ochirish" style="padding:3px 8px; font-size:11.5px;">🗑</button></td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
  document.getElementById('sk-qoshish').addEventListener('click', async () => {
    const anketa = document.getElementById('sk-anketa').value.trim();
    if (!anketa) return;
    const res = await fetch(`${API_BASE}/sud/kunlari`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        anketa_raqami: anketa, sud_sanasi: document.getElementById('sk-sana').value.trim(),
        sud_vaqti: document.getElementById('sk-vaqt').value.trim(), sud_nomi: document.getElementById('sk-nomi').value.trim(),
        sud_ish_raqami: document.getElementById('sk-ish').value.trim(),
      }),
    });
    const d = await res.json();
    if (d.xato) { alert('Xato: ' + d.xato); return; }
    await sudKunlariBoliminiChizish();
  });
  document.getElementById('sk-excel').addEventListener('click', () => document.getElementById('sk-excel-file').click());
  document.getElementById('sk-excel-file').addEventListener('change', async () => {
    const f = document.getElementById('sk-excel-file').files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append('file', f);
    const res = await fetch(`${API_BASE}/sud/kunlari/excel_yuklash`, { method: 'POST', body: fd });
    const d = await res.json();
    alert(`Qo'shildi: ${d.qoshilgan} ta` + (d.xatolar && d.xatolar.length ? `\nXatolar:\n${d.xatolar.join('\n')}` : ''));
    await sudKunlariBoliminiChizish();
  });
  body.querySelectorAll('[data-act="sk-ochirish"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      await fetch(`${API_BASE}/sud/kunlari/${btn.dataset.id}`, { method: 'DELETE' });
      await sudKunlariBoliminiChizish();
    });
  });
}

// ---------------- SOZLAMALAR (umumiy) ----------------
const TALABNOMA_SOZLAMA_FIELDS = [
  ['bank_nomi', 'Bank nomi (to\'liq)'], ['bank_qisqa_nomi', 'Bank nomi (qisqa)'],
  ['bank_manzil', 'Bank manzili'], ['bank_email', 'Bank email'], ['bank_sayt', 'Bank sayti'],
  ['bank_tel', 'Bank markaziy tel'], ['bank_mobil_ilova', 'Mobil ilova nomi'], ['bank_kodi', 'Bank kodi'],
  ['aloqa_markazi_tel', 'Aloqa markazi tel'], ['filial_nomi', 'Filial nomi'], ['filial_tel', 'Filial telefon'],
  ['rahbar_ism', 'Filial rahbari F.I.Sh (standart)'],
  ['tolov_muddati_kun', "To'lov uchun beriladigan muddat (bank ish kuni)"],
  ['eslatma_muddati_kun', "Xat yuborish uchun ichki muddat (kun)"],
  ['dpd_chegara_kun', "Tahlil uchun DPD chegarasi (kun)"],
  ['minimal_qarz_summa', "Minimal qarz summasi (so'm) — shundan past bo'lsa, xat/Davo ariza tayyorlanmaydi"],
];

const DAVO_ARIZA_SOZLAMA_FIELDS = [
  ['davo_ariza_muddati_kun', "Xat yuborilgandan keyin Davo ariza tayyorlash muddati (kun)"],
  ['sud_topshirish_muddati_kun', "Palatadan qaytgandan keyin sudga topshirish muddati (kun)"],
  ['viloyat_nomi', 'Viloyat nomi (davo ariza uchun)'],
  ['sud_fuqarolik_nomi', 'Fuqarolik sudi nomi (jismoniy shaxslar uchun)'],
  ['sud_iqtisodiy_nomi', 'Iqtisodiy sudi nomi (yuridik shaxslar uchun)'],
  ['palata_nomi', "Savdo-Sanoat Palatasi bo'limi nomi"], ['bank_stir', 'Bank STIR'],
  ['bank_hisob_raqami_filial', 'Bank hisob raqami (filial)'], ['bank_kodi_filial', 'Bank kodi (filial)'],
  ['bank_hisob_raqami_bosh', 'Bank hisob raqami (bosh ofis)'], ['bank_kodi_bosh', 'Bank kodi (bosh ofis)'],
  ['bank_rasmiy_manzil_filial', "Bank rasmiy manzili (filial, sud hujjatlari uchun)"],
  ['pochta_xarajati_standart', "Standart pochta xarajati (so'm)"],
  ['sud_ariza_imzo_ism', 'Davo ariza imzolovchisi F.I.Sh'],
  ['sud_ariza_imzo_lavozimi', 'Davo ariza imzolovchisi lavozimi'],
];

const BH_SOZLAMA_FIELDS = [
  ['bh_hududiy_boshqarma', "Yuborilgan hudud (hududiy boshqarma)"],
  ['bh_masul_xodim', "Arizachi mas'ul xodimi (F.I.Sh)"],
  ['bh_masul_tel', "Arizachi telefon raqami"],
  ['bh_mfo', "Arizachi MFOsi"],
  ['bh_arizachi_turi', "Arizachi turi"],
];

const MIB_SOZLAMA_FIELDS = [
  ['mib_harakatsizlik_muddati_kun', "MIBda harakatsizlik ogohlantirish muddati (kun)"],
  ['bxm_miqdori', "BXM (bazaviy hisoblash miqdori), so'm"],
  ['mib_toxtatish_dpd_chegara', "MIB to'xtatish uchun DPD chegarasi (kun)"],
];

const VAFOT_SOZLAMA_FIELDS = [
  ['sugurta_javob_muddati_ish_kun', "Sug'urta javobini kutish muddati (ish kuni)"],
];

const SUGURTA_UNDIRISH_SOZLAMA_FIELDS = [
  ['sugurta_undirish_muddat_kun', "Ariza yuborilgandan keyin javob kutish muddati (kun) — o'tib ketsa ogohlantirish chiqadi"],
];

async function sugurtaKompaniyalarBolimiChizish(container) {
  const div = document.createElement('div');
  div.className = 'card';
  div.style = 'margin-top:16px;';
  container.appendChild(div);
  const chizish2 = async () => {
    const data = await apiGet('/sugurta_undirish/kompaniyalar');
    div.innerHTML = `
      <div class="card-h">Sug'urta kompaniyalari (o'zingiz belgilaysiz)</div>
      <div class="page-sub">Sug'urtadan undirish bo'limida kompaniya tanlashda shu ro'yxat taklif qilinadi. Yangi nom qo'lda yozilsa ham avtomatik shu ro'yxatga qo'shiladi.</div>
      <div class="btn-row">
        <input class="tb-input" id="suk-nomi" placeholder="Kompaniya nomi" style="width:280px;">
        <button class="btn-gold" id="suk-qoshish" style="margin-left:0;">+ Qo'shish</button>
      </div>
      <table style="width:100%; font-size:12.5px; margin-top:8px;">
        ${data.royxat.map(t => `<tr>
          <td style="padding:4px 0;">${xavfsizMatn(t.nomi)}</td>
          <td style="text-align:right;"><button class="btn danger" data-suk-id="${t.id}" style="padding:2px 8px; font-size:11px;">🗑 O'chirish</button></td>
        </tr>`).join('')}
      </table>
      ${data.royxat.length === 0 ? '<div class="page-sub">Hali kompaniya qo\'shilmagan.</div>' : ''}
    `;
    div.querySelector('#suk-qoshish').addEventListener('click', async () => {
      const nomi = div.querySelector('#suk-nomi').value.trim();
      if (!nomi) return;
      await fetch(`${API_BASE}/sugurta_undirish/kompaniyalar`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nomi }),
      });
      await chizish2();
    });
    div.querySelectorAll('[data-suk-id]').forEach(btn => {
      btn.addEventListener('click', async () => {
        await fetch(`${API_BASE}/sugurta_undirish/kompaniyalar`, {
          method: 'DELETE', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: btn.dataset.sukId }),
        });
        await chizish2();
      });
    });
  };
  await chizish2();
}

async function mibHarakatTurlariBolimiChizish(container) {
  const div = document.createElement('div');
  div.className = 'card';
  div.style = 'margin-top:16px;';
  container.appendChild(div);
  const chizish2 = async () => {
    const data = await apiGet('/mib/harakat_turlari');
    div.innerHTML = `
      <div class="card-h">MIB harakat turlari (o'zingiz belgilaysiz)</div>
      <div class="page-sub">MIB bo'limida "+ Harakat" bosilganda tanlanadigan ro'yxat — shu yerda o'zingiz kerakli turlarni qo'shasiz.</div>
      <div class="btn-row">
        <input class="tb-input" id="mht-nomi" placeholder="Yangi harakat nomi (masalan: Bank hisobiga qaratildi)" style="width:280px;">
        <button class="btn-gold" id="mht-qoshish" style="margin-left:0;">+ Qo'shish</button>
      </div>
      <table style="width:100%; font-size:12.5px; margin-top:8px;">
        ${data.turlar.map(t => `<tr>
          <td style="padding:4px 0;">${xavfsizMatn(t.nomi)}</td>
          <td style="text-align:right;"><button class="btn danger" data-turi-id="${t.id}" style="padding:2px 8px; font-size:11px;">🗑 O'chirish</button></td>
        </tr>`).join('')}
      </table>
    `;
    div.querySelector('#mht-qoshish').addEventListener('click', async () => {
      const nomi = div.querySelector('#mht-nomi').value.trim();
      if (!nomi) return;
      await fetch(`${API_BASE}/mib/harakat_turlari`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nomi }),
      });
      await chizish2();
    });
    div.querySelectorAll('[data-turi-id]').forEach(btn => {
      btn.addEventListener('click', async () => {
        await fetch(`${API_BASE}/mib/harakat_turlari/${btn.dataset.turiId}`, { method: 'DELETE' });
        await chizish2();
      });
    });
  };
  await chizish2();
}

async function loginOqimi() {
  // Backend (ayniqsa yangi/notanish papkada, antivirus tekshiruvi
  // tufayli) ishga tushishi biroz vaqt olishi mumkin — shuning uchun
  // foydalanuvchiga jarayon davom etayotganini ko'rsatib, sabr bilan
  // (jami taxminan 30 soniyagacha) kutamiz.
  let holat = null;
  const jamiUrinish = 30;
  for (let i = 0; i < jamiUrinish; i++) {
    try {
      holat = await apiGet('/auth/status');
      break;
    } catch (e) {
      if (i === 2) {
        document.body.innerHTML = `
          <div style="display:flex; align-items:center; justify-content:center; height:100vh; background:var(--bg);">
            <div style="background:#fff; border-radius:14px; padding:36px 40px; width:420px; text-align:center;">
              <div style="font-size:32px; margin-bottom:10px;">⏳</div>
              <div style="font-size:15px; font-weight:600; color:var(--ink); margin-bottom:8px;">Backend ishga tushmoqda...</div>
              <div id="login-wait-msg" style="font-size:12.5px; color:var(--muted); line-height:1.6;">
                Iltimos, biroz kuting...
              </div>
            </div>
          </div>`;
      }
      if (i > 2) {
        const el = document.getElementById('login-wait-msg');
        if (el) el.textContent = `Hali urinilmoqda... (${i}/${jamiUrinish})`;
      }
      await new Promise(r => setTimeout(r, 1000));
    }
  }
  if (!holat) {
    document.body.innerHTML = `
      <div style="display:flex; align-items:center; justify-content:center; height:100vh; background:var(--bg);">
        <div style="background:#fff; border-radius:14px; padding:36px 40px; width:420px; text-align:center;">
          <div style="font-size:32px; margin-bottom:10px;">⚠️</div>
          <div style="font-size:16px; font-weight:700; color:var(--err); margin-bottom:8px;">Backend ishga tushmadi</div>
          <div style="font-size:12.5px; color:var(--muted); line-height:1.6;">
            Dastur orqa fon xizmati (backend.exe) bilan bog'lanib bo'lmadi.<br><br>
            Iltimos: 1) Antivirus dasturni bloklamaganini tekshiring,<br>
            2) Quyidagi tugma bilan qayta urinib ko'ring,<br>
            3) Muammo davom etsa, dasturni to'liq yopib, qayta oching.
          </div>
          <button class="btn-gold" id="login-retry-btn" style="margin-top:16px; margin-left:0;">🔄 Qayta urinish</button>
        </div>
      </div>`;
    document.getElementById('login-retry-btn').addEventListener('click', loginOqimi);
    return;
  }
  if (!holat.parol_kerak && !holat.kop_foydalanuvchi) {
    dasturniBoshlash();
    return;
  }
  loginEkraniniKorsatish(false, holat.kop_foydalanuvchi);
}

async function tarmoqSozlamasiDialogOchish() {
  if (!window.qarzNazorat) { alert("Bu funksiya faqat dastur (Electron) ichida ishlaydi."); return; }
  const joriy = await window.qarzNazorat.tarmoqSozlamasiniOlish();
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:400px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:8px;">Tarmoq sozlamasi</div>
      <div style="font-size:12.5px; color:var(--muted); line-height:1.6; margin-bottom:12px;">
        Agar bu kompyuter <b>mijoz</b> bo'lib, boshqa (server) kompyuterdagi umumiy bazaga ulanishi kerak bo'lsa — o'sha kompyuterning tarmoqdagi IP manzilini kiriting (masalan 192.168.1.50). <b>Bo'sh qoldirsangiz</b> — bu kompyuter mustaqil/server sifatida ishlaydi.
      </div>
      <input class="tb-input" id="ts-ip" style="width:100%; margin-bottom:12px;" placeholder="Server IP manzili (masalan 192.168.1.50)" value="${joriy.server_ip || ''}">
      <div style="display:flex; justify-content:flex-end; gap:8px;">
        <button class="btn" id="ts-cancel">Bekor qilish</button>
        <button class="btn-gold" id="ts-save" style="margin-left:0;">✓ Saqlash va qayta ishga tushirish</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  document.getElementById('ts-cancel').addEventListener('click', () => overlay.remove());
  document.getElementById('ts-save').addEventListener('click', async () => {
    const ip = document.getElementById('ts-ip').value.trim();
    const ok = await window.qarzNazorat.tarmoqSozlamasiniSaqlash(ip);
    if (!ok) {
      alert("Xato: sozlama saqlanmadi! Iltimos, dasturni administrator sifatida ishga tushirib qayta urinib ko'ring.");
      return;
    }
    // MUHIM: saqlanganini o'zimiz qayta o'qib, ANIQ tasdiqlaymiz —
    // shundan keyingina qayta ishga tushiramiz. Aks holda, agar biror
    // sabab bilan fayl "yozildi" deyilib, aslida noto'g'ri saqlangan
    // bo'lsa, foydalanuvchi bexabar qolib, dastur yana o'zining lokal
    // bazasiga kirib ketishi mumkin edi.
    const tekshiruv = await window.qarzNazorat.tarmoqSozlamasiniOlish();
    if ((tekshiruv.server_ip || '') !== ip) {
      alert("Xato: sozlama saqlanganda tasdiqlab bo'lmadi. Qayta urinib ko'ring.");
      return;
    }
    await window.qarzNazorat.dasturniQaytaIshgaTushirish();
  });
}

function loginEkraniniKorsatish(xato, kopFoydalanuvchi) {
  document.body.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:center; height:100vh; background:var(--bg);">
      <div style="background:#fff; border-radius:14px; padding:36px 40px; width:340px; box-shadow:0 10px 40px rgba(20,27,77,0.12);">
        <div style="font-size:20px; font-weight:700; color:var(--navy); margin-bottom:4px;">🏦 Qarz Nazorat</div>
        <div style="font-size:12.5px; color:var(--muted); margin-bottom:20px;">Kirish uchun ${kopFoydalanuvchi ? "login va parolni" : "parolni"} kiriting</div>
        ${kopFoydalanuvchi ? `<input type="text" id="login-login" class="tb-input" style="width:100%; padding:11px; font-size:14px; margin-bottom:10px;" placeholder="Login" autofocus>` : ''}
        <input type="password" id="login-parol" class="tb-input" style="width:100%; padding:11px; font-size:14px; margin-bottom:10px;" placeholder="Parol" ${kopFoydalanuvchi ? '' : 'autofocus'}>
        ${xato ? `<div style="color:var(--err); font-size:12.5px; margin-bottom:10px;">${kopFoydalanuvchi ? "Login yoki parol noto'g'ri" : "Parol noto'g'ri"}, qaytadan urinib ko'ring.</div>` : ''}
        <button class="btn-gold" id="login-btn" style="width:100%; margin-left:0; justify-content:center;">Kirish</button>
        <div style="text-align:center; margin-top:14px;">
          <a href="#" id="login-tarmoq-sozlama" style="font-size:11.5px; color:var(--muted);">⚙ Tarmoq sozlamasi</a>
        </div>
      </div>
    </div>
  `;
  document.getElementById('login-tarmoq-sozlama').addEventListener('click', (e) => { e.preventDefault(); tarmoqSozlamasiDialogOchish(); });
  const parolInput = document.getElementById('login-parol');
  const loginInput = document.getElementById('login-login');
  const loginBtn = document.getElementById('login-btn');
  const urinishFn = async () => {
    const parol = parolInput.value;
    const login = loginInput ? loginInput.value : '';
    const r = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ parol, login }),
    });
    const data = await r.json();
    if (data.ok) {
      if (data.foydalanuvchi) window._joriyFoydalanuvchi = data.foydalanuvchi;
      document.body.innerHTML = `
        <div class="app">
          <nav class="sidebar" id="sidebar">
            <div class="sb-title">🏦 Qarz Nazorat</div>
            <div class="sb-sub">Talabnoma Tizimi</div>
            <div class="sb-line"></div>
            <div class="sb-items" id="sb-items"></div>
          </nav>
          <main class="main" id="main-content">
            <div class="loading">Yuklanmoqda...</div>
          </main>
        </div>`;
      dasturniBoshlash();
    } else {
      loginEkraniniKorsatish(true, kopFoydalanuvchi);
    }
  };
  loginBtn.addEventListener('click', urinishFn);
  parolInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') urinishFn(); });
  if (loginInput) loginInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') parolInput.focus(); });
}

function dasturniBoshlash() {
  // MUHIM TUZATISH: "Backend ishga tushmadi" ekrani (va login ekrani)
  // butun `document.body` ni almashtiradi — ya'ni dasturning asosiy
  // tuzilmasi (sidebar va asosiy maydon) o'chib ketadi. Ilgari "Qayta
  // urinish" tugmasi bosilganda, backend allaqachon ishga tushgan bo'lsa
  // ham, `sidebarQurish()` yo'q elementga murojaat qilib xato berardi va
  // oyna MANGU BO'SH qolib ketardi. Endi tuzilma yo'q bo'lsa — qayta
  // quriladi.
  dasturTuzilmasiniTiklash();
  sidebarQurish();
  ekranniOchish('bosh_sahifa');
}

function dasturTuzilmasiniTiklash() {
  if (document.getElementById('sb-items') && document.getElementById('main-content')) return;
  document.body.innerHTML = `
    <div class="app">
      <nav class="sidebar" id="sidebar">
        <div class="sb-title">🏦 Qarz Nazorat</div>
        <div class="sb-sub">Talabnoma Tizimi</div>
        <div class="sb-line"></div>
        <div class="sb-items" id="sb-items"></div>
      </nav>
      <main class="main" id="main-content">
        <div class="loading">Yuklanmoqda...</div>
      </main>
    </div>`;
}

// ═══ HUQUQIY JARAYON TAHLILI ══════════════════════════════════════════
// Mavjud "Tahlil" PORTFELNI tahlil qiladi; bu esa ISHNING O'ZINI:
// voronka, bosqich davomiyligi, undirish manbalari, oylik dinamika va
// MIB harakatlarining samaradorligi.
//
// Ranglar: uchta qatordagi (xat / sud / MIB) ranglar tekshiruvdan
// o'tkazilgan — rang ko'rish buzilishi (daltonizm) bo'lganda ham
// bir-biridan ajralib turadi, va oq fonda kontrasti yetarli.
