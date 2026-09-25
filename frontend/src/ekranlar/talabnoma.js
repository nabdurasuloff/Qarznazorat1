// Talabnoma (ogohlantirish xatlari) ekrani.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

// ---------------- TALABNOMA ----------------
let talabnomaBelgilangan = new Set();

let talabnomaRoyxatCache = [];

let talabnomaSubTab = 'royxat';

const TALABNOMA_SAHIFA_HAJMI = 200;

let talabnomaKorsatilganSoni = TALABNOMA_SAHIFA_HAJMI;

async function talabnomaniYuklash(main) {
  main.innerHTML = `
    <div class="page-title">Talabnoma tayyorlash</div>
    <div style="display:flex; gap:8px; margin-bottom:14px;">
      <button class="btn" id="tn-subtab-royxat" style="${talabnomaSubTab === 'royxat' ? 'background:var(--navy);color:#fff;' : ''}">Yuborilishi kerak bo'lgan xatlar</button>
      <button class="btn" id="tn-subtab-hisobot" style="${talabnomaSubTab === 'hisobot' ? 'background:var(--navy);color:#fff;' : ''}">Yuborilgan xatlar hisoboti</button>
    </div>
    <div id="tn-body"></div>
  `;
  document.getElementById('tn-subtab-royxat').addEventListener('click', () => { talabnomaSubTab = 'royxat'; talabnomaniYuklash(main); });
  document.getElementById('tn-subtab-hisobot').addEventListener('click', () => { talabnomaSubTab = 'hisobot'; talabnomaniYuklash(main); });

  if (talabnomaSubTab === 'hisobot') {
    await talabnomaHisobotiniChizish();
    return;
  }

  const body = document.getElementById('tn-body');
  body.innerHTML = `
    <div class="page-sub" id="tn-sub">Yuklanmoqda...</div>

    <div class="card">
      <div class="btn-row" style="align-items:center;">
        <select class="field-select" id="tn-format" style="width:120px;">
          <option>Word (.docx)</option>
          <option>PDF (.pdf)</option>
        </select>
        <label style="font-size:12.5px; display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="tn-only-new" checked> Faqat yangi
        </label>
        <span style="width:1px; height:22px; background:var(--border); margin:0 2px;"></span>
        <span style="font-size:12.5px; color:var(--muted); align-self:center;">Paket:</span>
        <select class="tb-select" id="tn-paket" style="width:70px;">
          <option>10</option><option selected>30</option><option>50</option><option>100</option><option>Barchasi</option>
        </select>
        <button class="btn" id="tn-first-paket">① Birinchi paket</button>
        <button class="btn" id="tn-excel-export">📊 Excel eksport</button>
        <button class="btn" id="tn-excel-import">📥 Excel yuklash</button>
        <input type="file" id="tn-file-input" accept=".xlsx,.xls" style="display:none;">
        <span style="width:1px; height:22px; background:var(--border); margin:0 2px;"></span>
        <input class="tb-input" id="tn-search-input" placeholder="🔍 Anketa №" style="width:110px;">
        <button class="btn" id="tn-search-btn">Qidirish</button>
        <button class="btn" id="tn-send-single">✉ Yuborish</button>
      </div>
      <div class="btn-row" style="margin-top:8px;">
        <button class="btn" id="tn-refresh">🔄 Yangilash</button>
        <button class="btn" id="tn-select-all">☑ Hammasini belgilash</button>
        <button class="btn" id="tn-select-none">☐ Belgilarni bekor qilish</button>
        <span class="badge-count" id="tn-count" style="margin-left:auto;">Belgilangan: 0 ta</span>
        <button class="btn-gold" id="tn-generate-btn" style="margin-left:0;">✉ Xat yaratish (ommaviy)</button>
      </div>
    </div>

    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th></th><th>Anketa №</th><th>Mijoz nomi</th><th>Turi</th>
            <th>DPD (kun)</th><th>Muddati o'tgan qarz</th><th>Bazada mavjud?</th>
          </tr></thead>
          <tbody id="tn-tbody"></tbody>
        </table>
      </div>
    </div>
    <div style="text-align:center; padding: 14px 0;" id="tn-more-wrap"></div>
  `;

  document.getElementById('tn-refresh').addEventListener('click', () => talabnomaRoyxatniYangilash());
  document.getElementById('tn-select-all').addEventListener('click', () => {
    talabnomaRoyxatCache.forEach(r => talabnomaBelgilangan.add(r.anketa_raqami));
    talabnomaJadvalniChizish();
  });
  document.getElementById('tn-select-none').addEventListener('click', () => {
    talabnomaBelgilangan.clear();
    talabnomaJadvalniChizish();
  });
  document.getElementById('tn-only-new').addEventListener('change', () => talabnomaRoyxatniYangilash());
  document.getElementById('tn-generate-btn').addEventListener('click', talabnomaXatYaratish);
  document.getElementById('tn-tbody').addEventListener('click', talabnomaTbodyClickTinglovchisi);

  document.getElementById('tn-first-paket').addEventListener('click', () => {
    const paket = document.getElementById('tn-paket').value;
    const n = paket === 'Barchasi' ? talabnomaRoyxatCache.length : parseInt(paket, 10);
    talabnomaBelgilangan.clear();
    talabnomaRoyxatCache.slice(0, n).forEach(r => talabnomaBelgilangan.add(r.anketa_raqami));
    talabnomaKorsatilganSoni = Math.max(talabnomaKorsatilganSoni, n);
    talabnomaJadvalniChizish();
  });

  document.getElementById('tn-excel-export').addEventListener('click', async () => {
    if (talabnomaBelgilangan.size === 0) {
      alert("Avval ro'yxatdan mijozlarni tanlang ('Birinchi paket' yordam beradi).");
      return;
    }
    const r = await fetch(`${API_BASE}/talabnoma/excel_eksport`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anketalar: Array.from(talabnomaBelgilangan) }),
    });
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'talabnoma_royxati.xlsx'; a.click();
    URL.revokeObjectURL(url);
  });

  document.getElementById('tn-excel-import').addEventListener('click', () => {
    document.getElementById('tn-file-input').click();
  });
  document.getElementById('tn-file-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch(`${API_BASE}/talabnoma/excel_import`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    let msg = `${data.yangilandi} ta mijoz manzili/ma'lumoti yangilandi.`;
    if (data.summa_yangilandi) msg += `\n${data.summa_yangilandi} ta mijozning krediti summasi saqlandi.`;
    if (data.otkazib_yuborildi) msg += `\n${data.otkazib_yuborildi} ta qator o'tkazib yuborildi.`;
    alert(msg);
    e.target.value = '';
    await talabnomaRoyxatniYangilash();
  });

  document.getElementById('tn-search-btn').addEventListener('click', talabnomaBittaQidirish);
  document.getElementById('tn-search-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') talabnomaBittaQidirish();
  });
  document.getElementById('tn-send-single').addEventListener('click', async () => {
    const anketa = document.getElementById('tn-search-input').value.trim();
    if (!anketa) { alert('Anketa raqamini kiriting.'); return; }
    const r = await fetch(`${API_BASE}/talabnoma/xat_yaratish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anketalar: [anketa] }),
    });
    const data = await r.json();
    if (data.yaratildi) alert(`Xat tayyorlandi: ${anketa}`);
    else alert(`Xat tayyorlanmadi.\n${data.xatolar.join(', ')}`);
    await talabnomaRoyxatniYangilash();
  });

  await talabnomaRoyxatniYangilash();
}

async function talabnomaHisobotiniChizish() {
  try {
    const body = document.getElementById('tn-body');
    if (!body) return;
    body.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;
    const data = await apiGet('/talabnoma/xatlar_hisoboti');
    const bodyYana = document.getElementById('tn-body');
    if (!bodyYana) return; // Foydalanuvchi boshqa ekranga o'tib ketgan bo'lishi mumkin
    window._tnHisobotCache = data.royxat;
    window._tnHisobotBelgilangan = new Set();
    body.innerHTML = `
      <div class="page-sub">Barcha yaratilgan/yuborilgan xatlar tarixi ("so'nggi qilingan ishlar"). Jami: ${data.jami} ta.</div>
      <div class="primary-bar">
        <span style="color:var(--ice); font-size:12.5px;">Belgilangan xatlarni 'Yuborildi' deb belgilash.</span>
        <span class="badge-count" id="th-count" style="margin-left:auto;">Belgilangan: 0 ta</span>
        <button class="btn-gold" id="th-mark-sent">✓ Yuborildi deb belgilash</button>
      </div>
      <div class="toolbar">
        <input class="tb-input" id="th-qidiruv" placeholder="Anketa raqami" style="width:130px;">
        <button class="btn" id="th-qidirish-btn">🔍 Topish</button>
        <button class="btn" id="th-select-all">☑ Hammasi</button>
        <button class="btn" id="th-select-none">☐ Bekor qilish</button>
      </div>
      <div class="toolbar">
        <button class="btn danger" id="th-delete-selected">🗑 Tanlanganlarni o'chirish</button>
        <button class="btn danger" id="th-delete-all-tayyor">🗑 Barcha 'Tayyor'ni tozalash</button>
        <button class="btn" id="th-clean-duplicates">🧹 Dublikatlarni tozalash</button>
      </div>
      <div class="table-wrap">
        <div class="table-scroll">
          <table>
            <thead><tr>
              <th></th><th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Xat turi</th><th>Holat</th>
              <th>Yaratilgan sana</th><th>Yuborilgan sana</th><th></th>
            </tr></thead>
            <tbody id="th-tbody"></tbody>
          </table>
        </div>
      </div>
    `;
    thHisobotJadvalniChizish();

    document.getElementById('th-mark-sent').addEventListener('click', async () => {
      if (window._tnHisobotBelgilangan.size === 0) { alert('Xatni tanlang.'); return; }
      await fetch(`${API_BASE}/talabnoma/xat_yuborildi_belgilash_ommaviy`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(window._tnHisobotBelgilangan) }),
      });
      if (talabnomaSubTab === 'hisobot') await talabnomaHisobotiniChizish();
    });
    document.getElementById('th-select-all').addEventListener('click', () => {
      window._tnHisobotCache.forEach(r => window._tnHisobotBelgilangan.add(r.id));
      thHisobotJadvalniChizish();
    });
    document.getElementById('th-select-none').addEventListener('click', () => {
      window._tnHisobotBelgilangan.clear();
      thHisobotJadvalniChizish();
    });
    document.getElementById('th-qidirish-btn').addEventListener('click', async () => {
      const anketa = document.getElementById('th-qidiruv').value.trim();
      if (!anketa) return;
      const res = await apiGet(`/talabnoma/xat_qidirish?anketa=${encodeURIComponent(anketa)}`);
      res.ids.forEach(id => window._tnHisobotBelgilangan.add(id));
      thHisobotJadvalniChizish();
    });
    document.getElementById('th-delete-selected').addEventListener('click', async () => {
      if (window._tnHisobotBelgilangan.size === 0) { alert('O\'chirish uchun xat tanlang.'); return; }
      if (!confirm(`${window._tnHisobotBelgilangan.size} ta xat bazadan o'chiriladi (faqat 'Tayyor'/'Muddati o'tgan' holatidagilar). Davom etaymi?`)) return;
      const r = await fetch(`${API_BASE}/talabnoma/xat_ochirish`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(window._tnHisobotBelgilangan) }),
      });
      const res = await r.json();
      alert(`${res.ochirildi} ta xat o'chirildi.${res.otkazib_yuborildi ? ' ' + res.otkazib_yuborildi + " ta 'Yuborildi' holatida bo'lgani uchun o'tkazib yuborildi." : ''}`);
      if (talabnomaSubTab === 'hisobot') await talabnomaHisobotiniChizish();
    });
    document.getElementById('th-delete-all-tayyor').addEventListener('click', async () => {
      if (!confirm("Hali yuborilmagan (Tayyor + Muddati o'tgan) barcha xatlar butunlay o'chiriladi. Davom etaymi?")) return;
      const r = await fetch(`${API_BASE}/talabnoma/barcha_tayyor_ochirish`, { method: 'POST' });
      const res = await r.json();
      alert(`${res.ochirildi} ta xat o'chirildi.`);
      if (talabnomaSubTab === 'hisobot') await talabnomaHisobotiniChizish();
    });
    document.getElementById('th-clean-duplicates').addEventListener('click', async () => {
      if (!confirm("Dublikat (bir anketaga bir nechta) xatlar tozalanadi, har biriga eng muhim yozuv qoldiriladi. Davom etaymi?")) return;
      const r = await fetch(`${API_BASE}/talabnoma/dublikatlarni_tozalash`, { method: 'POST' });
      const res = await r.json();
      alert(res.topildi === 0 ? "Dublikat topilmadi." : `${res.ochirildi} ta dublikat yozuv o'chirildi.`);
      if (talabnomaSubTab === 'hisobot') await talabnomaHisobotiniChizish();
    });
  } catch (e) {
    const xatoJoy = document.querySelector('#mib-body, #sud-body, #tn-body') || document.getElementById('main-content');
    if (xatoJoy) xatoJoy.innerHTML = `<div class="page-sub" style="color:var(--err);">Xato yuz berdi: ${e.message}</div>`;
  }

}

async function talabnomaBittaQidirish() {
  const anketa = document.getElementById('tn-search-input').value.trim();
  if (!anketa) return;
  const data = await apiGet(`/talabnoma/qidirish?anketa=${encodeURIComponent(anketa)}`);
  talabnomaRoyxatCache = data.royxat;
  talabnomaKorsatilganSoni = TALABNOMA_SAHIFA_HAJMI;
  document.getElementById('tn-sub').textContent = `Qidiruv natijasi: ${data.royxat.length} ta topildi.`;
  talabnomaJadvalniChizish();
}

async function talabnomaRoyxatniYangilash() {
  const onlyNewEl = document.getElementById('tn-only-new');
  if (!onlyNewEl) return; // Foydalanuvchi shu orada boshqa sub-tabga o'tib ketgan
  const onlyNew = onlyNewEl.checked;
  document.getElementById('tn-sub').textContent = 'Yuklanmoqda...';
  const data = await apiGet(`/talabnoma/royxat?only_new=${onlyNew}`);
  if (!document.getElementById('tn-sub')) return; // So'rov davomida ekran almashtirilgan
  talabnomaRoyxatCache = data.royxat;
  talabnomaBelgilangan.clear();
  talabnomaKorsatilganSoni = TALABNOMA_SAHIFA_HAJMI;
  document.getElementById('tn-sub').textContent =
    `45+ kun muddati o'tgan mijozlar: ${data.royxat.length} ta (jami tahlil qilingan ${data.jami} tadan)`;
  talabnomaJadvalniChizish();
}

function talabnomaJadvalniChizish() {
  const tbody = document.getElementById('tn-tbody');
  if (!tbody) return; // Foydalanuvchi shu orada boshqa sub-tabga/ekranga o'tib ketgan bo'lishi mumkin
  const korsatiladigan = talabnomaRoyxatCache.slice(0, talabnomaKorsatilganSoni);
  tbody.innerHTML = korsatiladigan.map(r => {
    const checked = talabnomaBelgilangan.has(r.anketa_raqami);
    return `<tr>
      <td><span class="checkbox ${checked ? 'checked' : ''}" data-anketa="${r.anketa_raqami}"></span></td>
      <td>${r.anketa_raqami}</td>
      <td>${xavfsizMatn(r.mijoz_nomi)}</td>
      <td>${r.turi}</td>
      <td>${r.dpd}</td>
      <td>${formatSum(r.jami_qarz)}</td>
      <td>${r.mijoz_topildi ? "✓ Ha" : "Yo'q"}</td>
    </tr>`;
  }).join('');
  document.getElementById('tn-count').textContent = `Belgilangan: ${talabnomaBelgilangan.size} ta`;

  const moreWrap = document.getElementById('tn-more-wrap');
  const qolgan = talabnomaRoyxatCache.length - talabnomaKorsatilganSoni;
  if (qolgan > 0) {
    moreWrap.innerHTML = `<button class="btn ghost" id="tn-more-btn">
      ⬇ Yana ${Math.min(qolgan, TALABNOMA_SAHIFA_HAJMI)} tasini ko'rsatish (jami ${qolgan} ta qoldi)
    </button>`;
    document.getElementById('tn-more-btn').addEventListener('click', () => {
      talabnomaKorsatilganSoni += TALABNOMA_SAHIFA_HAJMI;
      talabnomaJadvalniChizish();
    });
  } else {
    moreWrap.innerHTML = '';
  }
}

function talabnomaTbodyClickTinglovchisi(e) {
  const el = e.target.closest('.checkbox');
  if (!el) return;
  const anketa = el.dataset.anketa;
  if (talabnomaBelgilangan.has(anketa)) {
    talabnomaBelgilangan.delete(anketa);
    el.classList.remove('checked');
  } else {
    talabnomaBelgilangan.add(anketa);
    el.classList.add('checked');
  }
  document.getElementById('tn-count').textContent = `Belgilangan: ${talabnomaBelgilangan.size} ta`;
}

async function talabnomaXatYaratish() {
  if (talabnomaBelgilangan.size === 0) {
    alert("Kamida bitta mijozni belgilang.");
    return;
  }
  const btn = document.getElementById('tn-generate-btn');
  btn.textContent = 'Tayyorlanmoqda...';
  btn.disabled = true;
  try {
    const r = await fetch(`${API_BASE}/talabnoma/xat_yaratish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        anketalar: Array.from(talabnomaBelgilangan),
        format: document.getElementById('tn-format').value.includes('PDF') ? 'pdf' : 'docx',
      }),
    });
    // MUHIM: server ichki xato (500) qaytarsa, javob JSON emas — HTML
    // bo'ladi va `r.json()` xato beradi. Ilgari bu xato hech qayerda
    // ushlanmasdi: tugma oddiy holatiga qaytar, LEKIN hech qanday xabar
    // chiqmasdi — foydalanuvchi xatlar tayyorlangan deb o'ylab ketardi.
    if (!r.ok) {
      let xabar = `So'rov muvaffaqiyatsiz tugadi (HTTP ${r.status}).`;
      try { const d = await r.json(); if (d.xato) xabar = d.xato; } catch (e) { /* JSON emas */ }
      alert('Xato: ' + xabar);
      return;
    }
    const data = await r.json();
    let msg = `${data.yaratildi} ta xat tayyorlandi ('Tayyor' holatida).`;
    if (data.otkazib_yuborildi) msg += `\n${data.otkazib_yuborildi} ta anketa uchun xat allaqachon mavjud edi.`;
    if (data.xatolar && data.xatolar.length) msg += `\nXatolar: ${data.xatolar.join(', ')}`;
    alert(msg);
    await talabnomaRoyxatniYangilash();
  } catch (e) {
    alert("Xatlarni yaratishda xato: " + e.message +
          "\n\nServer ishlayotganini tekshiring va qaytadan urinib ko'ring.");
  } finally {
    btn.textContent = '✉ Tanlanganlar uchun xat yaratish (ommaviy)';
    btn.disabled = false;
  }
}

// ---------------- DAVO ARIZA ----------------
