// Davo ariza ekrani.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

// ---------------- DAVO ARIZA ----------------
let davoBelgilangan = new Set();

let davoRoyxatCache = [];

let davoTurlari = {};

async function davoArizaniYuklash(main) {
  const turlariData = await apiGet('/davo-ariza/turlari');
  davoTurlari = turlariData.turlari;
  const turOptions = Object.entries(davoTurlari).map(([k, v]) => `<option value="${k}">${v}</option>`).join('');

  main.innerHTML = `
    <div class="page-title">Davo ariza tayyorlash</div>
    <div class="page-sub" id="da-sub">Faqat xati 'Yuborildi' deb belgilangan mijozlar ro'yxatda ko'rinadi.</div>

    <div class="primary-bar">
      <div style="flex:1; max-width:280px;">
        <div class="field-label">Ariza turi (qo'lda tanlash uchun)</div>
        <select class="field-select" id="da-turi" style="width:100%;">${turOptions}</select>
      </div>
      <span class="badge-count" id="da-count" style="margin-left:0;">Belgilangan: 0 ta</span>
      <button class="btn-gold" id="da-generate-btn">⚖ Tanlanganlar uchun Davo ariza tayyorlash</button>
    </div>

    <div class="card">
      <div class="btn-row" style="align-items:center;">
        <input class="tb-input" id="da-qidiruv" placeholder="🔍 Anketa raqami" style="width:130px;">
        <button class="btn" id="da-qidirish-btn">Topish</button>
        <select class="tb-select" id="da-paket" style="width:70px;">
          <option>10</option><option selected>30</option><option>50</option><option>100</option><option>Barchasi</option>
        </select>
        <button class="btn" id="da-first-paket">① Birinchi paket</button>
        <span style="width:1px; height:22px; background:var(--border); margin:0 2px;"></span>
        <select class="tb-select" id="da-holat-filter">
          <option value="">Holat: Barchasi</option>
          <option value="yoq">Hali tayyorlanmagan</option>
          <option value="tayyor">Tayyor (kutilmoqda)</option>
          <option value="olib_kelindi">Olib kelindi</option>
          <option value="otgan">Muddati o'tgan</option>
        </select>
        <select class="tb-select" id="da-turi-filter">
          <option value="">Turi: Barchasi</option>
          <option value="jismoniy">Jismoniy</option>
          <option value="yuridik">Yuridik</option>
          <option value="yatt">YaTT</option>
        </select>
        <select class="tb-select" id="da-tavsiya-filter">
          <option value="">Tayyorlangan turi: Barchasi</option>
          ${Object.entries(davoTurlari).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}
        </select>
      </div>
      <div class="btn-row" style="margin-top:8px; align-items:center;">
        <span style="font-size:12.5px; color:var(--muted);">Tayyorlangan sanasi:</span>
        <input type="date" class="tb-input" id="da-sana-dan" style="width:150px;">
        <span style="font-size:12.5px; color:var(--muted);">—</span>
        <input type="date" class="tb-input" id="da-sana-gacha" style="width:150px;">
        <button class="btn" id="da-sana-tozalash">✕</button>
        <span style="width:1px; height:22px; background:var(--border); margin:0 2px;"></span>
        <button class="btn" id="da-select-all">☑ Hammasi</button>
        <button class="btn" id="da-select-none">☐ Bekor qilish</button>
        <button class="btn" id="da-refresh">🔄 Yangilash</button>
      </div>
      <div class="btn-row" style="margin-top:8px;">
        ${ochiladiganMenyu('da-taminot-dd', "🛡 Ta'minot", `
          <button class="btn" id="da-taminot-kiritish" style="display:block; width:100%; text-align:left; margin-bottom:4px;">✏ Kafil/garov kiritish (bitta belgilangan)</button>
          <button class="btn" id="da-taminot-excel-out" style="display:block; width:100%; text-align:left; margin-bottom:4px;">📊 Excel eksport</button>
          <button class="btn" id="da-taminot-excel-in" style="display:block; width:100%; text-align:left;">📥 Excel yuklash</button>
          <input type="file" id="da-taminot-file" accept=".xlsx,.xls" style="display:none;">
        `)}
        ${ochiladiganMenyu('da-tasdiq-dd', "✓ Tasdiqlash", `
          <button class="btn" id="da-olib-kelindi" style="display:block; width:100%; text-align:left; margin-bottom:4px;">✓ Olib kelindi (bitta belgilangan)</button>
          <button class="btn" id="da-imzodan-excel" style="display:block; width:100%; text-align:left; margin-bottom:4px;">📥 Imzodan Excel</button>
          <button class="btn" id="da-sud-excel" style="display:block; width:100%; text-align:left;">⚖ Sudga topshirilganlar</button>
        `)}
        ${ochiladiganMenyu('da-belgilangan-dd', "⚙ Belgilanganlar bilan", `
          <button class="btn" id="da-reestr" style="display:block; width:100%; text-align:left; margin-bottom:4px;">📋 SSPga Reestr tayyorlash</button>
          <button class="btn ghost" id="da-birlashtir" style="display:block; width:100%; text-align:left; margin-bottom:4px;">📎 Bitta faylga birlashtirish</button>
          <button class="btn danger" id="da-ochirish" style="display:block; width:100%; text-align:left;">🗑 Tayyorlangan arizani o'chirish</button>
        `)}
        <button class="btn-gold" id="da-hisobot-excel" style="margin-left:auto;">📊 To'liq hisobot (Excel)</button>
      </div>
    </div>

    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th></th><th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Jami qarz</th>
            <th>Davo summasi</th><th>Davo ariza holati</th><th>Tayyorlangan sanasi</th><th>Summa farqi</th><th>Ish raqami</th><th>Ta'minot</th><th>Tavsiya etilgan turi</th>
          </tr></thead>
          <tbody id="da-tbody"></tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById('da-refresh').addEventListener('click', davoRoyxatniYangilash);
  ochiladiganMenyuIshga('da-taminot-dd');
  ochiladiganMenyuIshga('da-tasdiq-dd');
  ochiladiganMenyuIshga('da-belgilangan-dd');
  document.getElementById('da-select-all').addEventListener('click', () => {
    davoJadvalFiltrlangan().forEach(r => davoBelgilangan.add(r.anketa_raqami));
    davoJadvalniChizish();
  });
  document.getElementById('da-select-none').addEventListener('click', () => {
    davoBelgilangan.clear();
    davoJadvalniChizish();
  });
  document.getElementById('da-holat-filter').addEventListener('change', davoJadvalniChizish);
  document.getElementById('da-turi-filter').addEventListener('change', davoJadvalniChizish);
  document.getElementById('da-tavsiya-filter').addEventListener('change', davoJadvalniChizish);
  document.getElementById('da-sana-dan').addEventListener('change', davoJadvalniChizish);
  document.getElementById('da-sana-gacha').addEventListener('change', davoJadvalniChizish);
  document.getElementById('da-sana-tozalash').addEventListener('click', () => {
    document.getElementById('da-sana-dan').value = '';
    document.getElementById('da-sana-gacha').value = '';
    davoJadvalniChizish();
  });
  document.getElementById('da-tbody').addEventListener('click', davoTbodyClick);
  document.getElementById('da-generate-btn').addEventListener('click', davoArizaYaratish);

  document.getElementById('da-first-paket').addEventListener('click', () => {
    const paket = document.getElementById('da-paket').value;
    const royxat = davoJadvalFiltrlangan();
    const n = paket === 'Barchasi' ? royxat.length : parseInt(paket, 10);
    davoBelgilangan.clear();
    royxat.slice(0, n).forEach(r => davoBelgilangan.add(r.anketa_raqami));
    davoJadvalniChizish();
  });
  document.getElementById('da-qidirish-btn').addEventListener('click', () => {
    const anketa = document.getElementById('da-qidiruv').value.trim();
    if (!anketa) return;
    window._daQidiruv = anketa;
    const topilgan = davoJadvalFiltrlangan();
    if (topilgan.length === 0) { alert("Bu anketa 'Davo Ariza' ro'yxatida topilmadi."); window._daQidiruv = ''; return; }
    davoJadvalniChizish();
  });
  document.getElementById('da-qidiruv').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') document.getElementById('da-qidirish-btn').click();
  });

  document.getElementById('da-taminot-kiritish').addEventListener('click', davoTaminotDialogOchish);
  document.getElementById('da-olib-kelindi').addEventListener('click', davoOlibKelindiDialogOchish);

  document.getElementById('da-taminot-excel-out').addEventListener('click', () =>
    davoFileDownloadPost('/davo-ariza/taminot_excel_eksport', { anketalar: Array.from(davoBelgilangan) }, 'taminot.xlsx'));
  document.getElementById('da-imzodan-excel').addEventListener('click', () =>
    davoFileDownloadPost('/davo-ariza/imzodan_excel_eksport', {}, 'imzodan_kelganlar.xlsx'));
  document.getElementById('da-sud-excel').addEventListener('click', () => {
    faylniYuklabOlish(`${API_BASE}/davo-ariza/sudga_topshirilganlar_excel`);
  });
  document.getElementById('da-hisobot-excel').addEventListener('click', () => {
    faylniYuklabOlish(`${API_BASE}/davo-ariza/hisobot_excel`);
  });

  document.getElementById('da-taminot-excel-in').addEventListener('click', () => {
    document.getElementById('da-taminot-file').click();
  });
  document.getElementById('da-taminot-file').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch(`${API_BASE}/davo-ariza/taminot_excel_import`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    alert(`${data.yangilandi} ta ta'minot yozuvi yangilandi.`);
    e.target.value = '';
    await davoRoyxatniYangilash();
  });

  document.getElementById('da-reestr').addEventListener('click', davoReestrOchish);
  document.getElementById('da-birlashtir').addEventListener('click', async () => {
    if (davoBelgilangan.size < 2) { alert('Kamida 2 ta mijozni belgilang.'); return; }
    await davoFileDownloadPost('/davo-ariza/birlashtir', { anketalar: Array.from(davoBelgilangan) }, 'Birlashgan_Davo_arizalar.docx');
  });
  document.getElementById('da-ochirish').addEventListener('click', async () => {
    if (davoBelgilangan.size === 0) { alert('Kamida bitta mijozni belgilang.'); return; }
    if (!confirm(`${davoBelgilangan.size} ta mijozning Davo arizasi o'chiriladi. Davom etaymi?`)) return;
    const r = await fetch(`${API_BASE}/davo-ariza/ochirish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anketalar: Array.from(davoBelgilangan) }),
    });
    const data = await r.json();
    alert(`${data.ochirildi} ta o'chirildi. ${data.otkazib_yuborildi ? data.otkazib_yuborildi + ' ta o\'tkazib yuborildi.' : ''}`);
    await davoRoyxatniYangilash();
  });

  await davoRoyxatniYangilash();
}

function davoTaminotDialogOchish() {
  if (davoBelgilangan.size !== 1) { alert("Aynan bitta mijozni belgilang."); return; }
  const anketa = Array.from(davoBelgilangan)[0];
  apiGet(`/davo-ariza/taminot?anketa=${encodeURIComponent(anketa)}`).then(current => {
    const overlay = document.createElement('div');
    overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
    overlay.innerHTML = `
      <div style="background:#fff;border-radius:12px;padding:20px 24px;width:460px;max-height:80vh;overflow-y:auto;">
        <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Ta'minot ma'lumotlari — ${anketa}</div>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <label>Ta'minot turi
            <select class="tb-select" id="td-turi" style="width:100%;">
              <option value="yoq">yoq</option><option value="kafillik">kafillik</option>
              <option value="garov">garov</option><option value="kafillik_garov">kafillik_garov</option>
            </select>
          </label>
          <label>Kafil F.I.Sh <input class="tb-input" id="td-kafil_ism" style="width:100%;"></label>
          <label>Kafil manzili <input class="tb-input" id="td-kafil_manzil" style="width:100%;"></label>
          <label>Garov mulki tavsifi <textarea class="tb-input" id="td-garov_tavsifi" style="width:100%;" rows="2"></textarea></label>
          <label>Garov bahosi (so'm) <input class="tb-input" id="td-garov_bahosi" style="width:100%;"></label>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
          <button class="btn" id="td-cancel">Bekor qilish</button>
          <button class="btn-gold" id="td-save" style="margin-left:0;">✓ Saqlash</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    document.getElementById('td-turi').value = current.taminot_turi || 'yoq';
    document.getElementById('td-kafil_ism').value = current.kafil_ism || '';
    document.getElementById('td-kafil_manzil').value = current.kafil_manzil || '';
    document.getElementById('td-garov_tavsifi').value = current.garov_tavsifi || '';
    document.getElementById('td-garov_bahosi').value = current.garov_bahosi || '';
    document.getElementById('td-cancel').addEventListener('click', () => overlay.remove());
    document.getElementById('td-save').addEventListener('click', async () => {
      await fetch(`${API_BASE}/davo-ariza/taminot`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          anketa_raqami: anketa,
          taminot_turi: document.getElementById('td-turi').value,
          kafil_ism: document.getElementById('td-kafil_ism').value,
          kafil_manzil: document.getElementById('td-kafil_manzil').value,
          garov_tavsifi: document.getElementById('td-garov_tavsifi').value,
          garov_bahosi: document.getElementById('td-garov_bahosi').value,
        }),
      });
      overlay.remove();
      await davoRoyxatniYangilash();
    });
  });
}

function davoOlibKelindiDialogOchish() {
  if (davoBelgilangan.size !== 1) { alert("Aynan bitta mijozni belgilang."); return; }
  const anketa = Array.from(davoBelgilangan)[0];
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:400px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Olib kelindi deb belgilash — ${anketa}</div>
      <label style="display:block;margin-bottom:8px;">Ish raqami<br><input class="tb-input" id="ok-ish" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Sana (kun.oy.yil)<br><input class="tb-input" id="ok-sana" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">SSPdan olib kelingan hujjat skani (PDF) — <b style="color:var(--err);">majburiy</b><br>
        <input type="file" id="ok-skan" accept=".pdf" style="width:100%; margin-top:4px;"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="ok-cancel">Bekor qilish</button>
        <button class="btn-gold" id="ok-save" style="margin-left:0;">✓ Saqlash</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  document.getElementById('ok-cancel').addEventListener('click', () => overlay.remove());
  document.getElementById('ok-save').addEventListener('click', async () => {
    const ish = document.getElementById('ok-ish').value.trim();
    const sana = document.getElementById('ok-sana').value.trim();
    const skanFile = document.getElementById('ok-skan').files[0];
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
    await davoRoyxatniYangilash();
  });
}

function davoReestrOchish() {
  if (davoBelgilangan.size === 0) { alert('Kamida bitta mijozni belgilang.'); return; }
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:380px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">SSPga Reestr xati</div>
      <label style="display:block;margin-bottom:8px;">Chiquvchi xat raqami<br><input class="tb-input" id="rs-raqam" style="width:100%;" placeholder="03/999"></label>
      <label style="display:block;margin-bottom:8px;">Sana<br><input class="tb-input" id="rs-sana" style="width:100%;" value="${new Date().toLocaleDateString('uz-UZ')}"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="rs-cancel">Bekor qilish</button>
        <button class="btn-gold" id="rs-save" style="margin-left:0;">✓ Tayyorlash</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  document.getElementById('rs-cancel').addEventListener('click', () => overlay.remove());
  document.getElementById('rs-save').addEventListener('click', async () => {
    const raqam = document.getElementById('rs-raqam').value.trim();
    const sana = document.getElementById('rs-sana').value.trim();
    if (!raqam || !sana) { alert('Xat raqami va sanani kiriting.'); return; }
    overlay.remove();
    await davoFileDownloadPost('/davo-ariza/reestr',
      { anketalar: Array.from(davoBelgilangan), xat_raqami: raqam, xat_sanasi: sana }, 'Reestr_SSP.docx');
  });
}

async function davoRoyxatniYangilash() {
  document.getElementById('da-sub').textContent = 'Yuklanmoqda...';
  const data = await apiGet('/davo-ariza/royxat');
  davoRoyxatCache = data.royxat;
  davoBelgilangan.clear();
  window._daQidiruv = '';
  document.getElementById('da-sub').textContent =
    `Faqat xati 'Yuborildi' deb belgilangan mijozlar ro'yxatda ko'rinadi. Jami: ${data.royxat.length} ta.`;
  davoJadvalniChizish();
}

function davoSanaTaqqoslash(ddMmYyyy, yyyyMmDd, turi) {
  // r.tayyorlangan_sana formati: "09.09.2026" (kun.oy.yil)
  // HTML date input formati: "2026-09-09" (yil-oy-kun)
  if (!ddMmYyyy) return false;
  const [kun, oy, yil] = ddMmYyyy.split('.');
  const solishtirish = `${yil}-${oy}-${kun}`;
  if (turi === 'dan') return solishtirish >= yyyyMmDd;
  return solishtirish <= yyyyMmDd;
}

function davoJadvalFiltrlangan() {
  const holatFiltr = document.getElementById('da-holat-filter').value;
  const turiFiltr = document.getElementById('da-turi-filter').value;
  const tavsiyaFiltr = document.getElementById('da-tavsiya-filter').value;
  const sanaDan = document.getElementById('da-sana-dan').value;
  const sanaGacha = document.getElementById('da-sana-gacha').value;
  const qidiruv = (window._daQidiruv || '').trim();
  return davoRoyxatCache.filter(r => {
    if (holatFiltr && r.holat !== holatFiltr) return false;
    if (turiFiltr && r.turi !== turiFiltr) return false;
    if (tavsiyaFiltr && r.tavsiya_kaliti !== tavsiyaFiltr) return false;
    if (qidiruv && r.anketa_raqami !== qidiruv) return false;
    if (sanaDan && !davoSanaTaqqoslash(r.tayyorlangan_sana, sanaDan, 'dan')) return false;
    if (sanaGacha && !davoSanaTaqqoslash(r.tayyorlangan_sana, sanaGacha, 'gacha')) return false;
    return true;
  });
}

function davoJadvalniChizish() {
  const royxat = davoJadvalFiltrlangan();
  const tbody = document.getElementById('da-tbody');
  tbody.innerHTML = royxat.map(r => {
    const checked = davoBelgilangan.has(r.anketa_raqami);
    return `<tr>
      <td><span class="checkbox ${checked ? 'checked' : ''}" data-anketa="${r.anketa_raqami}"></span></td>
      <td>${r.anketa_raqami}</td>
      <td>${xavfsizMatn(r.mijoz_nomi)}</td>
      <td>${r.turi}</td>
      <td>${formatSum(r.jami_qarz)}</td>
      <td>${r.davo_summasi ? formatSum(r.davo_summasi) : '—'}</td>
      <td>${davoHolatPill(r.holat, r.holat_matni)}</td>
      <td>${r.tayyorlangan_sana || '—'}</td>
      <td>${r.qoshimcha_kerak ? `<span style="color:var(--err); font-weight:600;">${r.summa_farqi_matn}</span>` : r.summa_farqi_matn}</td>
      <td>${r.ish_raqami || '—'}</td>
      <td>${r.taminot_bor ? '✓' : '—'}</td>
      <td>${r.tavsiya_nomi}</td>
    </tr>`;
  }).join('');
  document.getElementById('da-count').textContent = `Belgilangan: ${davoBelgilangan.size} ta`;
}

function davoTbodyClick(e) {
  const el = e.target.closest('.checkbox');
  if (!el) return;
  const anketa = el.dataset.anketa;
  if (davoBelgilangan.has(anketa)) {
    davoBelgilangan.delete(anketa);
    el.classList.remove('checked');
  } else {
    davoBelgilangan.add(anketa);
    el.classList.add('checked');
  }
  document.getElementById('da-count').textContent = `Belgilangan: ${davoBelgilangan.size} ta`;
}

async function davoArizaYaratish() {
  if (davoBelgilangan.size === 0) {
    alert('Kamida bitta mijozni belgilang.');
    return;
  }
  const btn = document.getElementById('da-generate-btn');
  btn.textContent = 'Tayyorlanmoqda...';
  btn.disabled = true;
  try {
    const r = await fetch(`${API_BASE}/davo-ariza/yaratish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anketalar: Array.from(davoBelgilangan) }),
    });
    const data = await r.json();
    let msg = `${data.yaratildi} ta Davo ariza tayyorlandi.`;
    if (Object.keys(data.turlar_soni).length) {
      const taqsimot = Object.entries(data.turlar_soni)
        .map(([k, v]) => `${davoTurlari[k] || k}: ${v} ta`).join(', ');
      msg += `\n\n${taqsimot}`;
    }
    if (data.otkazib_yuborildi) msg += `\n\n${data.otkazib_yuborildi} ta anketa uchun Davo ariza allaqachon mavjud edi.`;
    if (data.xatolar.length) msg += `\n\nXatolar: ${data.xatolar.join(', ')}`;
    alert(msg);
    await davoRoyxatniYangilash();
  } finally {
    btn.textContent = '⚖ Tanlanganlar uchun Davo ariza tayyorlash';
    btn.disabled = false;
  }
}

// ---------------- SUD ISHLARI ----------------
