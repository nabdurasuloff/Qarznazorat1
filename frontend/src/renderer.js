// Qarz Nazorat — asosiy frontend mantiq. Sidebar navigatsiyasi va
// har bir ekranni backend API'dan ma'lumot olib ko'rsatish shu yerda.

const SIDEBAR_ITEMS = [
  { key: 'bosh_sahifa', icon: '🏠', label: 'Bosh sahifa' },
  { key: 'portfel', icon: '📁', label: 'Portfel' },
  { key: 'mijozlar', icon: '👥', label: 'Mijozlar bazasi' },
  { key: 'tahlil', icon: '📊', label: 'Tahlil' },
  { key: 'reja_grafik', icon: '📅', label: 'Reja Grafik' },
  { key: 'talabnoma', icon: '✉', label: 'Talabnoma' },
  { key: 'davo_ariza', icon: '📄', label: 'Davo Ariza' },
  { key: 'sud', icon: '⚖', label: 'SUD Ishlari' },
  { key: 'mib', icon: '🏛', label: 'MIB ijro harakatlari' },
  { key: 'vafot', icon: '🕊', label: 'Vafot etganlar' },
  { key: '95413', icon: '📋', label: '95413' },
  { key: 'chora', icon: '🎯', label: "Chora ko'rish" },
  { key: 'sozlamalar', icon: '⚙️', label: 'Sozlamalar' },
];

let API_BASE = 'http://127.0.0.1:8877/api';

async function apiGet(path) {
  const r = await fetch(`${API_BASE}${path}`);
  if (!r.ok) throw new Error(`API xato: ${r.status}`);
  return r.json();
}

function ochiladiganMenyu(id, label, itemsHtml) {
  return `
    <div class="dropdown-wrap" style="position:relative; display:inline-block;">
      <button class="btn" id="${id}-btn">${label} ▾</button>
      <div class="dropdown-menu" id="${id}-menu" style="display:none; position:fixed; background:#fff; border:1px solid #E2E5EC; border-radius:8px; box-shadow:0 4px 16px rgba(0,0,0,0.12); padding:6px; min-width:230px; z-index:999;">
        ${itemsHtml}
      </div>
    </div>`;
}

function ochiladiganMenyuIshga(id) {
  const btn = document.getElementById(`${id}-btn`);
  const menu = document.getElementById(`${id}-menu`);
  if (!btn || !menu) return;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const ochiqmi = menu.style.display === 'block';
    document.querySelectorAll('.dropdown-menu').forEach(m => { m.style.display = 'none'; });
    if (!ochiqmi) {
      // MUHIM: menyu 'position:fixed' bo'lgani uchun, uni tugmaning
      // EKRANDAGI (skroll konteynerdan mustaqil) haqiqiy joylashuviga
      // qarab joylashtiramiz — aks holda jadval ichidagi skroll
      // konteynerlar uni "kesib" tashlab, ko'rinmas qilib qo'yardi.
      const rect = btn.getBoundingClientRect();
      menu.style.top = (rect.bottom + 4) + 'px';
      let left = rect.left;
      const oynaKengligi = window.innerWidth;
      if (left + 230 > oynaKengligi) left = Math.max(8, oynaKengligi - 240);
      menu.style.left = left + 'px';
      menu.style.display = 'block';
    }
  });
  document.addEventListener('click', (e) => {
    if (!menu.contains(e.target) && e.target !== btn) menu.style.display = 'none';
  });
}

function formatSum(n) {
  if (n === null || n === undefined) return '—';
  return Math.round(n).toLocaleString('ru-RU').replace(/,/g, ' ');
}

// ---------------- SIDEBAR ----------------
function sidebarQurish() {
  const container = document.getElementById('sb-items');
  container.innerHTML = '';
  SIDEBAR_ITEMS.forEach(item => {
    const el = document.createElement('div');
    el.className = 'sb-item';
    el.dataset.key = item.key;
    el.innerHTML = `<span>${item.icon}</span><span>${item.label}</span>`;
    el.addEventListener('click', () => ekranniOchish(item.key));
    container.appendChild(el);
  });
}

function faolBolimniBelgilash(key) {
  document.querySelectorAll('.sb-item').forEach(el => {
    el.classList.toggle('active', el.dataset.key === key);
  });
}

// ---------------- EKRANLAR ----------------
const EKRAN_YUKLOVCHILAR = {
  bosh_sahifa: boshSahifaniYuklash,
  portfel: portfelniYuklash,
  mijozlar: mijozlarBazasiniYuklash,
  talabnoma: talabnomaniYuklash,
  davo_ariza: davoArizaniYuklash,
  sud: sudIshlariniYuklash,
  mib: mibIjroniYuklash,
  chora: choraKorishniYuklash,
  '95413': nazorat95413niYuklash,
  tahlil: tahlilniYuklash,
  vafot: vafotEtganlarniYuklash,
  reja_grafik: rejaGrafikniYuklash,
  sozlamalar: umumiySozlamalarniYuklash,
};

async function ekranniOchish(key) {
  faolBolimniBelgilash(key);
  const main = document.getElementById('main-content');
  main.innerHTML = '<div class="loading">Yuklanmoqda...</div>';

  const yuklovchi = EKRAN_YUKLOVCHILAR[key];
  if (yuklovchi) {
    try {
      await yuklovchi(main);
    } catch (e) {
      main.innerHTML = `<div class="loading">Xato: ${e.message}</div>`;
    }
  } else {
    main.innerHTML = `<div class="page-title">${key}</div>
      <div class="page-sub">Bu bo'lim hali ishlab chiqilmoqda...</div>`;
  }
}

// ---------------- BOSH SAHIFA ----------------
async function boshSahifaniYuklash(main) {
  const [data, kunlik, tarixData] = await Promise.all([
    apiGet('/dashboard/summary'), apiGet('/reja/kunlik'), apiGet('/tahlil/tarix'),
  ]);
  const tarix = tarixData.tarix;

  const jiddiyMuammolar = [];
  if (data.muddati_otgan_xatlar > 0) jiddiyMuammolar.push(`${data.muddati_otgan_xatlar} ta xat muddati o'tgan`);
  if (data.davo_muddati_otgan > 0) jiddiyMuammolar.push(`${data.davo_muddati_otgan} ta Davo ariza muddati o'tgan`);
  if (data.sud_muddati_otgan > 0) jiddiyMuammolar.push(`${data.sud_muddati_otgan} ta sudga topshirish muddati o'tgan`);
  if (data.mib_harakatsiz > 0) jiddiyMuammolar.push(`${data.mib_harakatsiz} ta MIB ishi harakatsiz qolgan`);

  main.innerHTML = `
    <div class="page-title">Qarz Nazorat va Talabnoma Tizimi</div>
    <div class="page-sub">Portfelni tahlil qiling, muddati o'tgan mijozlarga xat tayyorlang.</div>

    ${jiddiyMuammolar.length > 0 ? `
    <div style="background:linear-gradient(135deg,#C0392B,#8A2417); color:#fff; border-radius:12px; padding:14px 20px; margin-bottom:18px; display:flex; align-items:center; gap:12px; font-size:13.5px; font-weight:600; box-shadow:0 4px 14px rgba(192,57,43,0.25);">
      <span style="font-size:22px;">⚠️</span>
      <span>Diqqat: ${jiddiyMuammolar.join(', ')}. Tezroq chora ko'ring!</span>
    </div>` : ''}

    <div class="stat-row">
      <div class="stat-card" data-goto="portfel" style="cursor:pointer;">
        <div class="stat-num">${formatSum(data.portfeldagi_kreditlar)}</div>
        <div class="stat-label">Portfeldagi kreditlar</div>
      </div>
      <div class="stat-card" data-goto="talabnoma" style="cursor:pointer;">
        <div class="stat-num">${formatSum(data.kun45_otgan)}</div>
        <div class="stat-label">45+ kun muddati o'tgan</div>
      </div>
      <div class="stat-card" data-goto="talabnoma" style="cursor:pointer;">
        <div class="stat-num ${data.yuborilmagan_xatlar > 0 ? 'warn' : ''}">${formatSum(data.yuborilmagan_xatlar)}</div>
        <div class="stat-label">Yuborilmagan xatlar</div>
      </div>
      <div class="stat-card" data-goto="talabnoma" style="cursor:pointer;">
        <div class="stat-num ${data.muddati_otgan_xatlar > 0 ? 'warn' : ''}">${formatSum(data.muddati_otgan_xatlar)}</div>
        <div class="stat-label">Muddati o'tgan xatlar</div>
      </div>
    </div>

    <div class="card-row">
      <div class="card">
        <div class="card-h">Bugungi ish kuni rejasi</div>
        ${kunlik.turkumlar.map(t => `
          <div style="display:flex; justify-content:space-between; font-size:12.5px; padding:6px 0 2px;">
            <span>${t.nomi}</span><b>${t.bajarildi} / ${t.reja}</b>
          </div>
          <div style="background:#E3E7F0; height:8px; border-radius:4px; overflow:hidden;">
            <div style="background:var(--stamp); height:100%; width:${t.reja > 0 ? Math.min(t.bajarildi / t.reja * 100, 100) : 0}%;"></div>
          </div>
        `).join('')}
      </div>
      <div class="card">
        <div class="card-h">Bugungi harakatlar</div>
        <div style="display:flex; gap:24px; padding: 6px 0;">
          <div><div class="stat-num" style="font-size:22px;">${formatSum(data.bugun_yaratilgan)}</div>
               <div class="stat-label">Bugun yaratilgan xatlar</div></div>
          <div><div class="stat-num" style="font-size:22px;">${formatSum(data.bugun_yuborilgan)}</div>
               <div class="stat-label">Bugun yuborilgan xatlar</div></div>
        </div>
      </div>
    </div>

    ${tarix.length >= 2 ? `
    <div class="card" style="margin-bottom:16px;">
      <div class="card-h">📈 Umumiy portfel tendensiyasi — 45+ kun (Stage 3) o'tganlar soni</div>
      <div style="position:relative; height:150px;"><canvas id="bs-trend-chart"></canvas></div>
    </div>` : ''}

    <div class="card-h" style="margin-bottom:10px;">Diqqat talab qiladigan holatlar</div>
    <div class="stat-row">
      <div class="stat-card" data-goto="davo_ariza" style="cursor:pointer;">
        <div class="stat-num ${data.davo_muddati_otgan > 0 ? 'warn' : ''}">${formatSum(data.davo_muddati_otgan)}</div>
        <div class="stat-label">Davo ariza muddati o'tgan</div>
      </div>
      <div class="stat-card" data-goto="sud" style="cursor:pointer;">
        <div class="stat-num ${data.sud_muddati_otgan > 0 ? 'warn' : ''}">${formatSum(data.sud_muddati_otgan)}</div>
        <div class="stat-label">Sudga topshirish muddati o'tgan</div>
      </div>
      <div class="stat-card" data-goto="mib" style="cursor:pointer;">
        <div class="stat-num ${data.mib_harakatsiz > 0 ? 'warn' : ''}">${formatSum(data.mib_harakatsiz)}</div>
        <div class="stat-label">MIB harakatsiz qolganlar</div>
      </div>
      <div class="stat-card" data-goto="chora" style="cursor:pointer;">
        <div class="stat-num ${data.chora_soni > 0 ? 'warn' : ''}">${formatSum(data.chora_soni)}</div>
        <div class="stat-label">Chora ko'rish kerak</div>
      </div>
      <div class="stat-card" data-goto="vafot" style="cursor:pointer;">
        <div class="stat-num ${data.sugurta_kutilmoqda > 0 ? 'warn' : ''}">${formatSum(data.sugurta_kutilmoqda)}</div>
        <div class="stat-label">Sug'urta javobi kutilmoqda</div>
      </div>
      <div class="stat-card" data-goto="talabnoma" style="cursor:pointer;">
        <div class="stat-num ${data.qayta_xat_kerak > 0 ? 'warn' : ''}">${formatSum(data.qayta_xat_kerak)}</div>
        <div class="stat-label">Qayta xat kerak (muddat o'tgan, chora ko'rilmagan)</div>
      </div>
    </div>

    <div class="card-h" style="margin-bottom:10px;">Tarmoq bo'yicha to'liq statistika (Stage 3)</div>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Tarmoq</th><th>Jami soni</th><th>Jami summa</th>
          <th>Jismoniy soni</th><th>Jismoniy summa</th>
          <th>Yuridik soni</th><th>Yuridik summa</th>
        </tr></thead>
        <tbody>
          ${data.tarmoq_jadval.map(r => `
            <tr>
              <td>${r.tarmoq}</td>
              <td>${formatSum(r.soni)}</td>
              <td>${formatSum(r.jami)}</td>
              <td>${formatSum(r.jismoniy_soni)}</td>
              <td>${formatSum(r.jismoniy_jami)}</td>
              <td>${formatSum(r.yuridik_soni)}</td>
              <td>${formatSum(r.yuridik_jami)}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>

    <div class="card-h" style="margin: 20px 0 10px;">So'nggi harakatlar</div>
    <div class="card" style="margin-bottom:14px;">
      <div class="page-sub" style="margin:0 0 10px;">Mijozni anketa raqami bo'yicha qidirish (butun portfel bo'yicha, qaysi bosqichda ekanini ko'rish uchun):</div>
      <div class="btn-row">
        <input class="tb-input" id="bs-qidiruv" placeholder="Anketa raqami" style="width:160px;">
        <button class="btn-gold" id="bs-qidirish-btn" style="margin-left:0;">🔍 Qidirish</button>
      </div>
    </div>

    <div class="table-wrap">
      <table>
        <thead><tr><th>Sana</th><th>Anketa №</th><th>Mijoz</th><th>Xat turi</th><th>Holat</th><th>Hujjatlar</th></tr></thead>
        <tbody id="bs-songgi-tbody"><tr><td colspan="6" class="loading">Yuklanmoqda...</td></tr></tbody>
      </table>
    </div>

    <div class="card" style="margin-top:20px;">
      <div class="card-h">Ishlash tartibi</div>
      <div style="font-size:13px; line-height:2;">
        1. 'Portfel' bo'limida .xlsb faylni yuklang.<br>
        2. 'Mijozlar bazasi' bo'limida jismoniy/yuridik shaxslar ma'lumotini import qiling.<br>
        3. 'Talabnoma' bo'limida 45 kundan o'tgan mijozlarni ko'ring, xat yarating.<br>
        4. 'Talabnoma → Yuborilgan xatlar hisoboti' bo'limida yuborilganlarni belgilang — 3 kun ichida yuborilmasa, eslatma chiqadi.
      </div>
    </div>
  `;

  document.querySelectorAll('.stat-card[data-goto]').forEach(card => {
    card.addEventListener('click', () => ekranniOchish(card.dataset.goto));
  });

  document.getElementById('bs-qidirish-btn').addEventListener('click', boshSahifaQidirish);
  document.getElementById('bs-qidiruv').addEventListener('keydown', (e) => { if (e.key === 'Enter') boshSahifaQidirish(); });

  if (tarix.length >= 2) {
    new Chart(document.getElementById('bs-trend-chart'), {
      type: 'line',
      data: {
        labels: tarix.map(r => r.sana.slice(5)),
        datasets: [{ data: tarix.map(r => r.stage3_soni), borderColor: '#1E2761',
          backgroundColor: 'rgba(30,39,97,0.08)', fill: true, tension: 0.3 }],
      },
      options: { plugins: { legend: { display: false } }, maintainAspectRatio: false },
    });
  }

  apiGet('/dashboard/songgi_harakatlar').then(sData => {
    const tbody = document.getElementById('bs-songgi-tbody');
    if (!tbody) return;
    if (sData.royxat.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="loading">Hali hech qanday xat yaratilmagan.</td></tr>';
      return;
    }
    tbody.innerHTML = sData.royxat.map(r => `
      <tr><td>${r.sana}</td><td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.xat_turi}</td><td>${r.holat_matni}</td>
        <td>
          ${vafotFaylKnop(r.xat_fayl, 'Xat')}
          ${r.davo_fayl ? ' &nbsp; ' + vafotFaylKnop(r.davo_fayl, 'Davo ariza') : ''}
          ${r.sud_buyrugi_fayl ? ' &nbsp; ' + vafotFaylKnop(r.sud_buyrugi_fayl, 'Sud buyrugi') : ''}
          ${r.ijro_varaqasi_fayl ? ' &nbsp; ' + vafotFaylKnop(r.ijro_varaqasi_fayl, 'Ijro varaqasi') : ''}
          ${r.yakunlash_fayl ? ' &nbsp; ' + vafotFaylKnop(r.yakunlash_fayl, 'Yakunlash asosi') : ''}
        </td>
      </tr>`).join('');
  });
}

async function boshSahifaQidirish() {
  const anketa = document.getElementById('bs-qidiruv').value.trim();
  if (!anketa) return;
  const data = await apiGet(`/dashboard/qidirish?anketa=${encodeURIComponent(anketa)}`);
  if (!data.topildi) { alert(`Anketa №${anketa} bo'yicha portfelda hech narsa topilmadi.`); return; }
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:560px;max-height:80vh;overflow-y:auto;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Anketa №${anketa} — holat</div>
      ${data.natija.map(r => `
        <div class="card" style="margin-bottom:10px;">
          <div style="font-weight:600;">${r.mijoz_nomi} (${r.turi})</div>
          <div style="font-size:12.5px; color:var(--muted); margin:4px 0;">Qarzdorlik: ${formatSum(r.jami_qarz)}</div>
          <div style="font-size:13px; font-weight:600;">${r.bosqich}</div>
          ${r.mib_ish_raqami ? `<div style="font-size:12px; color:var(--muted);">MIB ish raqami: ${r.mib_ish_raqami}</div>` : ''}
          ${r.oxirgi_mib_amal ? `<div style="font-size:12px; color:var(--muted);">So'nggi MIB harakati: ${r.oxirgi_mib_amal}</div>` : ''}
          <div style="margin-top:8px; display:flex; gap:12px; flex-wrap:wrap;">
            ${vafotFaylKnop(r.xat_fayl, 'Xat')}
            ${vafotFaylKnop(r.davo_fayl, 'Davo ariza')}
            ${vafotFaylKnop(r.sud_buyrugi_fayl, "Sud buyrug'i")}
            ${vafotFaylKnop(r.ijro_varaqasi_fayl, 'Ijro varaqasi')}
            ${vafotFaylKnop(r.yakunlash_fayl, 'Yakunlash asosi')}
            ${vafotFaylKnop(r.yigma_jild_fayl, "Yig'ma jild")}
          </div>
        </div>
      `).join('')}
      <div style="display:flex; justify-content:flex-end; margin-top:10px;">
        <button class="btn" id="bs-natija-yopish">Yopish</button>
      </div>
    </div>`);
  overlay.querySelector('#bs-natija-yopish').addEventListener('click', () => overlay.remove());
}

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

function thHisobotJadvalniChizish() {
  const tbody = document.getElementById('th-tbody');
  if (!tbody) return; // Ekran almashtirilgan bo'lsa, jim chiqamiz (xato ko'rsatmaymiz)
  tbody.innerHTML = window._tnHisobotCache.map(r => {
    const checked = window._tnHisobotBelgilangan.has(r.id);
    const holatPill = { yuborildi: 'olib_kelindi', tayyor: 'tayyor', muddati_otgan: 'otgan' }[r.holat] || 'yoq';
    return `<tr>
      <td><span class="checkbox ${checked ? 'checked' : ''}" data-id="${r.id}"></span></td>
      <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.mijoz_turi}</td><td>${r.xat_turi}</td>
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
      <td>${r.mijoz_nomi}</td>
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
    const data = await r.json();
    let msg = `${data.yaratildi} ta xat tayyorlandi ('Tayyor' holatida).`;
    if (data.otkazib_yuborildi) msg += `\n${data.otkazib_yuborildi} ta anketa uchun xat allaqachon mavjud edi.`;
    if (data.xatolar.length) msg += `\nXatolar: ${data.xatolar.join(', ')}`;
    alert(msg);
    await talabnomaRoyxatniYangilash();
  } finally {
    btn.textContent = '✉ Tanlanganlar uchun xat yaratish (ommaviy)';
    btn.disabled = false;
  }
}

// ---------------- DAVO ARIZA ----------------
let davoBelgilangan = new Set();
let davoRoyxatCache = [];
let davoTurlari = {};

function davoHolatPill(holat, matn) {
  const klass = { olib_kelindi: 'pill-green', tayyor: 'pill-amber', otgan: 'pill-red', yoq: 'pill-gray' }[holat] || 'pill-gray';
  return `<span class="pill ${klass}">${matn}</span>`;
}

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
    window.open(`${API_BASE}/davo-ariza/sudga_topshirilganlar_excel`, '_blank');
  });
  document.getElementById('da-hisobot-excel').addEventListener('click', () => {
    window.open(`${API_BASE}/davo-ariza/hisobot_excel`, '_blank');
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
      <td>${r.mijoz_nomi}</td>
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
let sudSubTab = 'topshirish';
let sudBelgilangan = new Set();
let sudTopshirishCache = [];
let sudRoyxatCache = [];

async function sudIshlariniYuklash(main) {
  main.innerHTML = `
    <div class="page-title">Sud Ishlari</div>
    <div class="page-sub">Palatadan (SSPdan) qaytgan Davo arizalarni sudga topshirish va jarayonni kuzatish.</div>
    <div style="display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap;">
      <button class="btn ${sudSubTab === 'topshirish' ? 'ghost' : ''}" id="sud-tab-topshirish"
        style="${sudSubTab === 'topshirish' ? 'background:var(--navy);color:#fff;' : ''}">SSPdan o'tib sudga jo'natiladiganlar</button>
      <button class="btn ${sudSubTab === 'royxat' ? 'ghost' : ''}" id="sud-tab-royxat"
        style="${sudSubTab === 'royxat' ? 'background:var(--navy);color:#fff;' : ''}">Suddan o'tkazilgan / MIB jarayonida</button>
      <button class="btn ${sudSubTab === 'hisobot' ? 'ghost' : ''}" id="sud-tab-hisobot"
        style="${sudSubTab === 'hisobot' ? 'background:var(--navy);color:#fff;' : ''}">Hisobot</button>
      <button class="btn ${sudSubTab === 'kiritilmagan' ? 'ghost' : ''}" id="sud-tab-kiritilmagan"
        style="${sudSubTab === 'kiritilmagan' ? 'background:var(--navy);color:#fff;' : ''}">✕ Sudga kiritilmaganlar</button>
      <button class="btn ${sudSubTab === 'xarajatlar' ? 'ghost' : ''}" id="sud-tab-xarajatlar"
        style="${sudSubTab === 'xarajatlar' ? 'background:var(--navy);color:#fff;' : ''}">💵 Xarajatlar</button>
    </div>
    <div id="sud-body"></div>
  `;
  document.getElementById('sud-tab-topshirish').addEventListener('click', () => { sudSubTab = 'topshirish'; sudIshlariniYuklash(main); });
  document.getElementById('sud-tab-royxat').addEventListener('click', () => { sudSubTab = 'royxat'; sudIshlariniYuklash(main); });
  document.getElementById('sud-tab-hisobot').addEventListener('click', () => { sudSubTab = 'hisobot'; sudIshlariniYuklash(main); });
  document.getElementById('sud-tab-kiritilmagan').addEventListener('click', () => { sudSubTab = 'kiritilmagan'; sudIshlariniYuklash(main); });
  document.getElementById('sud-tab-xarajatlar').addEventListener('click', () => { sudSubTab = 'xarajatlar'; sudIshlariniYuklash(main); });

  if (sudSubTab === 'topshirish') await sudTopshirishBoliminiChizish();
  else if (sudSubTab === 'hisobot') await sudHisobotBoliminiChizish();
  else if (sudSubTab === 'kiritilmagan') await sudKiritilmaganBoliminiChizish();
  else if (sudSubTab === 'xarajatlar') await sudXarajatlarBoliminiChizish();
  else await sudRoyxatBoliminiChizish();
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
    a.download = nomi ? nomi[1] : 'jild.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(blobUrl);
  } catch (e) {
    alert("Jildni yuklab olishda xato: " + e.message);
  }
}

function sudYigmaJildDialogOchish(anketa) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `<div style="background:#fff;border-radius:12px;padding:20px 24px;width:600px;max-height:85vh;overflow-y:auto;" id="syj-modal-content"><div class="loading">Yuklanmoqda...</div></div>`;
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

async function sudYigmaJildModalniChizish(anketa, overlay) {
  const content = overlay.querySelector('#syj-modal-content');
  const r = await fetch(`${API_BASE}/sud/yigma_jild_holati?anketa=${encodeURIComponent(anketa)}`);
  const data = await r.json();
  if (data.xato) { content.innerHTML = `<div class="page-sub" style="color:var(--err);">${data.xato}</div>`; return; }
  content.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <div style="font-size:16px; font-weight:700;">Sud harakatlari yig'ma jildi — ${anketa}</div>
      <button class="btn" id="syj-yopish">✕</button>
    </div>
    <div class="btn-row" style="margin-bottom:12px;">
      <button class="btn" id="syj-jild-yarat">📁 Titulni yangilash</button>
      <button class="btn" id="syj-malumotnoma-yarat">📄 Ma'lumotnoma yaratish</button>
    </div>
    <table style="width:100%; font-size:12.5px;">
      <thead><tr style="text-align:left; color:var(--muted);"><th>Hujjat</th><th>Holati</th><th></th></tr></thead>
      <tbody>
        ${data.hujjatlar.map(h => `<tr>
          <td style="padding:6px 0;">${h.nomi}</td>
          <td>${h.mavjud
            ? `✓ Yuklangan &nbsp; <a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(h.fayl)}" target="_blank">👁 Ko'rish</a>`
            : "— Yo'q"}</td>
          <td>${!['Titul', 'Davo ariza', 'Xat'].includes(h.nomi) ? `
            <input type="file" id="syj-file-${h.maydon}" accept=".pdf" style="display:none;">
            <button class="btn" data-maydon="${h.maydon}" data-act="syj-upload" style="padding:3px 10px; font-size:11.5px;">📤 Yuklash</button>` : ''}
          </td>
        </tr>`).join('')}
      </tbody>
    </table>
    <div class="card" style="margin-top:12px; padding:10px 14px;">
      <div class="card-h" style="font-size:12.5px;">➕ Boshqa (ixtiyoriy) hujjat qo'shish</div>
      <div class="btn-row">
        <input class="tb-input" id="syj-qoshimcha-nomi" placeholder="Hujjat nomi (masalan: Guvohnoma)" style="width:200px;">
        <input type="file" id="syj-qoshimcha-file" style="width:220px;">
        <button class="btn-gold" id="syj-qoshimcha-qoshish" style="margin-left:0;">📤 Qo'shish</button>
      </div>
      ${data.qoshimcha_hujjatlar && data.qoshimcha_hujjatlar.length > 0 ? `
        <table style="width:100%; font-size:12.5px; margin-top:8px;">
          ${data.qoshimcha_hujjatlar.map(qh => `<tr>
            <td style="padding:4px 0;">${qh.hujjat_nomi}</td>
            <td><a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(qh.fayl_yoli)}" target="_blank">👁 Ko'rish</a></td>
            <td><button class="btn danger" data-qoshimcha-id="${qh.id}" style="padding:2px 8px; font-size:11px;">🗑</button></td>
          </tr>`).join('')}
        </table>
      ` : ''}
    </div>
    <div style="margin-top:14px; display:flex; gap:8px;">
      <button class="btn-gold" id="syj-ruxsat" style="margin-left:0;" ${data.toliqmi ? '' : 'disabled'}>
        ${data.ruxsat_berilgan ? '✓ Ruxsat berilgan' : "✓ Sudga yuborishga ruxsat berish"}
      </button>
      <button class="btn" id="syj-tayyor-jild">📥 Tayyor jildni olish (PDF)</button>
    </div>
    ${!data.toliqmi ? '<div class="page-sub" style="color:var(--err); margin-top:8px;">Ruxsat berish uchun barcha hujjatlar to\'liq yuklanishi kerak.</div>' : ''}
  `;
  content.querySelector('#syj-yopish').addEventListener('click', async () => {
    overlay.remove();
    // MUHIM: oyna yopilganda, agar shu vaqt ichida hujjat yuklangan/holat
    // o'zgargan bo'lsa, asosiy jadval ("Shakillantirish"/"Ko'rish"
    // ustuni) yangilangan holatni ko'rsatishi uchun qayta yuklaymiz.
    if (typeof sudTopshirishRoyxatniYangilash === 'function' && document.getElementById('sud-tbody')) {
      await sudTopshirishRoyxatniYangilash();
    }
  });
  content.querySelector('#syj-qoshimcha-qoshish').addEventListener('click', async () => {
    const nomi = content.querySelector('#syj-qoshimcha-nomi').value.trim();
    const f = content.querySelector('#syj-qoshimcha-file').files[0];
    if (!nomi || !f) { alert("Hujjat nomi va faylni tanlang."); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('hujjat_nomi', nomi);
    fd.append('file', f);
    const res = await fetch(`${API_BASE}/sud/qoshimcha_hujjat_yuklash`, { method: 'POST', body: fd });
    const d = await res.json();
    if (d.xato) { alert('Xato: ' + d.xato); return; }
    await sudYigmaJildModalniChizish(anketa, overlay);
  });
  content.querySelectorAll('[data-qoshimcha-id]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm("Bu qo'shimcha hujjatni o'chirasizmi?")) return;
      await fetch(`${API_BASE}/sud/qoshimcha_hujjat/${btn.dataset.qoshimchaId}`, { method: 'DELETE' });
      await sudYigmaJildModalniChizish(anketa, overlay);
    });
  });
  content.querySelector('#syj-jild-yarat').addEventListener('click', async () => {
    const res = await fetch(`${API_BASE}/sud/yigma_jild_yaratish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ anketa_raqami: anketa }),
    });
    const d = await res.json();
    if (d.xato) { alert('Xato: ' + d.xato); return; }
    await sudYigmaJildModalniChizish(anketa, overlay);
    await sudTopshirishRoyxatniYangilash();
  });
  content.querySelector('#syj-malumotnoma-yarat').addEventListener('click', async () => {
    const res = await fetch(`${API_BASE}/sud/malumotnoma_yaratish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ anketa_raqami: anketa }),
    });
    const d = await res.json();
    if (d.xato) { alert('Xato: ' + d.xato); return; }
    await sudYigmaJildModalniChizish(anketa, overlay);
  });
  content.querySelectorAll('[data-act="syj-upload"]').forEach(btn => {
    const fileInput = content.querySelector(`#syj-file-${btn.dataset.maydon}`);
    btn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', async () => {
      const f = fileInput.files[0];
      if (!f) return;
      const fd = new FormData();
      fd.append('anketa_raqami', anketa);
      fd.append('maydon', btn.dataset.maydon);
      fd.append('file', f);
      const res = await fetch(`${API_BASE}/sud/hujjat_yuklash`, { method: 'POST', body: fd });
      const d = await res.json();
      if (d.xato) { alert('Xato: ' + d.xato); return; }
      await sudYigmaJildModalniChizish(anketa, overlay);
    });
  });
  content.querySelector('#syj-ruxsat').addEventListener('click', async () => {
    const btn = content.querySelector('#syj-ruxsat');
    const eskiMatn = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Saqlanmoqda...';
    try {
      const res = await fetch(`${API_BASE}/sud/ruxsat_berish`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ anketa_raqami: anketa }),
      });
      if (!res.ok) {
        let xabar = `So'rov muvaffaqiyatsiz tugadi (HTTP ${res.status}).`;
        try { const d = await res.json(); if (d.xato) xabar = d.xato; } catch (e2) { /* javob JSON emas */ }
        alert('Xato: ' + xabar);
        btn.disabled = false;
        btn.textContent = eskiMatn;
        return;
      }
      const d = await res.json();
      if (d.xato) { alert('Xato: ' + d.xato); btn.disabled = false; btn.textContent = eskiMatn; return; }
      await sudYigmaJildModalniChizish(anketa, overlay);
    } catch (e) {
      // MUHIM: server bilan ALOQA umuman o'rnatilmasa (masalan tarmoq
      // uzilgan, server ishlamayotgan bo'lsa) — bu yerda ANIQ xato
      // ko'rsatiladi, aks holda tugma "bosiladi-yu", hech narsa
      // o'zgarmagandek jim qolib ketardi.
      alert("Serverga ulanishda xato: " + e.message + "\n\nTarmoq ulanishini yoki backend ishga tushganini tekshiring.");
      btn.disabled = false;
      btn.textContent = eskiMatn;
    }
  });
  content.querySelector('#syj-tayyor-jild').addEventListener('click', () => {
    tayyorJildYuklabOlish(`${API_BASE}/sud/tayyor_jild?anketa=${encodeURIComponent(anketa)}`);
  });
}

async function sudQarorBoliminiChizish() {
  const body = document.getElementById('sud-body');
  const data = await apiGet('/sud/qaror_kutilayotganlar');
  body.innerHTML = `
    <div class="page-sub">Sudga topshirilgan, qarori hali yuklanmagan ishlar — muddat holati bilan.</div>
    <div class="toolbar">
      <button class="btn-gold" id="sq-excel" style="margin-left:0;">📤 Excel yuklab olish</button>
    </div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr><th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Muddat</th><th>Holati</th><th></th></tr></thead>
          <tbody>
            ${data.royxat.map(r => `<tr>
              <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td>
              <td>${r.muddat_kun} kun</td>
              <td style="color:${r.muddati_otganmi ? 'var(--err)' : 'inherit'};">
                ${r.kun_qoldi === null ? '—' : (r.muddati_otganmi ? `${Math.abs(r.kun_qoldi)} kun o'tdi!` : `${r.kun_qoldi} kun qoldi`)}
              </td>
              <td><button class="btn" data-anketa="${r.anketa_raqami}" data-act="qaror-yuklash">📤 Qaror yuklash</button></td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
  document.getElementById('sq-excel').addEventListener('click', () => {
    tayyorJildYuklabOlish(`${API_BASE}/sud/qaror_kutilayotganlar_excel`);
  });
  body.querySelectorAll('[data-act="qaror-yuklash"]').forEach(btn => {
    btn.addEventListener('click', () => sudQarorYuklashDialog(btn.dataset.anketa));
  });
}

function sudQarorYuklashDialog(anketa) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:420px;max-height:85vh;overflow-y:auto;">
      <div style="font-size:16px;font-weight:700;margin-bottom:12px;">Sud qarorini yuklash — ${anketa}</div>
      <label style="display:block;margin-bottom:8px;">Natija<br>
        <select class="tb-select" id="sq-natija" style="width:100%;">
          <option value="bank_foydasiga">✓ Bank foydasiga</option>
          <option value="qisman">≈ Qisman</option>
          <option value="rad_etildi">✕ Rad etildi</option>
        </select>
      </label>
      <label style="display:block;margin-bottom:8px;">Sana<br><input class="tb-input" id="sq-sana" style="width:100%;"></label>
      <div id="sq-qisman-fields" style="display:none;">
        <label style="display:block;margin-bottom:8px;">Asosiy qarz farqi<br><input class="tb-input" id="sq-asosiy" style="width:100%;" value="0"></label>
        <label style="display:block;margin-bottom:8px;">Foiz farqi<br><input class="tb-input" id="sq-foiz" style="width:100%;" value="0"></label>
        <label style="display:block;margin-bottom:8px;">Penya farqi<br><input class="tb-input" id="sq-penya" style="width:100%;" value="0"></label>
        <label style="display:flex; align-items:center; gap:6px; margin-bottom:8px;"><input type="checkbox" id="sq-davlat-boji"> Davlat bojiga sherik</label>
      </div>
      <div id="sq-rad-fields" style="display:none;">
        <label style="display:block;margin-bottom:8px;">Rad etilish sababi<br><textarea class="tb-input" id="sq-rad-sababi" style="width:100%; min-height:60px;"></textarea></label>
      </div>
      <label style="display:block;margin-bottom:8px;">Qaror hujjati (PDF) — majburiy<br><input type="file" id="sq-file" accept=".pdf" style="width:100%; margin-top:4px;"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:14px;">
        <button class="btn" id="sq-cancel">Bekor qilish</button>
        <button class="btn-gold" id="sq-save" style="margin-left:0;">✓ Saqlash</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  document.getElementById('sq-cancel').addEventListener('click', () => overlay.remove());
  const natijaSelect = document.getElementById('sq-natija');
  natijaSelect.addEventListener('change', () => {
    document.getElementById('sq-qisman-fields').style.display = natijaSelect.value === 'qisman' ? 'block' : 'none';
    document.getElementById('sq-rad-fields').style.display = natijaSelect.value === 'rad_etildi' ? 'block' : 'none';
  });
  document.getElementById('sq-save').addEventListener('click', async () => {
    const f = document.getElementById('sq-file').files[0];
    if (!f) { alert('Qaror hujjati (PDF) yuklash majburiy.'); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('natija', natijaSelect.value);
    fd.append('sana', document.getElementById('sq-sana').value);
    fd.append('qaror_fayl', f);
    if (natijaSelect.value === 'qisman') {
      fd.append('qisman_asosiy_farq', document.getElementById('sq-asosiy').value);
      fd.append('qisman_foiz_farq', document.getElementById('sq-foiz').value);
      fd.append('qisman_penya_farq', document.getElementById('sq-penya').value);
      fd.append('davlat_boji_sherik', document.getElementById('sq-davlat-boji').checked ? 'true' : 'false');
    }
    if (natijaSelect.value === 'rad_etildi') {
      fd.append('rad_sababi', document.getElementById('sq-rad-sababi').value);
    }
    const r = await fetch(`${API_BASE}/sud/qaror_yuklash`, { method: 'POST', body: fd });
    const res = await r.json();
    if (res.xato) { alert('Xato: ' + res.xato); return; }
    overlay.remove();
    await sudQarorBoliminiChizish();
  });
}

async function sudXarajatlarBoliminiChizish() {
  const body = document.getElementById('sud-body');
  const data = await apiGet('/sud/xarajatlar');
  body.innerHTML = `
    <div class="page-sub">Sudga tasdiqlangan mijozlar bo'yicha pochta xarajatlari hisobi.</div>
    <div class="toolbar">
      <input class="tb-input" id="sx-anketa" placeholder="Anketa raqami" style="width:130px;">
      <input class="tb-input" id="sx-summa" placeholder="Summa" style="width:120px;">
      <button class="btn-gold" id="sx-qoshish" style="margin-left:0;">+ Qo'shish</button>
      <span style="width:1px; height:22px; background:var(--border); margin:0 2px;"></span>
      <button class="btn" id="sx-shablon">📤 Shablon yuklab olish</button>
      <button class="btn-gold" id="sx-excel-import" style="margin-left:0;">📥 Excel yuklash</button>
      <input type="file" id="sx-excel-file" accept=".xlsx,.xls" style="display:none;">
    </div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr><th>Anketa №</th><th>Mijoz</th><th>PINFL/STIR</th><th>Summa</th><th>Holati</th><th>MIB ish raqami</th><th></th></tr></thead>
          <tbody>
            ${data.royxat.map(x => `<tr>
              <td>${x.anketa_raqami}</td><td>${x.mijoz_nomi}</td><td>${x.pinfl_yoki_stir || '—'}</td>
              <td>${formatSum(x.summa)}</td>
              <td>${{'kutilmoqda': 'Kutilmoqda', 'mib_ochildi': 'MIB ish ochilgan', 'yakunlangan': '✓ Yakunlangan'}[x.holati]}</td>
              <td>${x.mib_ijro_ish_raqami || '—'}</td>
              <td>${x.holati === 'kutilmoqda' ? `<button class="btn" data-id="${x.id}" data-act="sx-mib-ochish">MIB ish ochish</button>` : ''}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
  document.getElementById('sx-qoshish').addEventListener('click', async () => {
    const anketa = document.getElementById('sx-anketa').value.trim();
    const summa = document.getElementById('sx-summa').value.trim();
    if (!anketa || !summa) return;
    const r = await fetch(`${API_BASE}/sud/xarajatlar`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anketa_raqami: anketa, summa: parseFloat(summa) }),
    });
    const res = await r.json();
    if (res.xato) { alert('Xato: ' + res.xato); return; }
    await sudXarajatlarBoliminiChizish();
  });
  document.getElementById('sx-shablon').addEventListener('click', () => {
    window.open(`${API_BASE}/sud/xarajatlar_shablon`, '_blank');
  });
  document.getElementById('sx-excel-import').addEventListener('click', () => document.getElementById('sx-excel-file').click());
  document.getElementById('sx-excel-file').addEventListener('change', async () => {
    const f = document.getElementById('sx-excel-file').files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append('file', f);
    const res = await fetch(`${API_BASE}/sud/xarajatlar_excel_yuklash`, { method: 'POST', body: fd });
    const d = await res.json();
    if (d.xato) { alert('Xato: ' + d.xato); return; }
    alert(`Qo'shildi: ${d.qoshilgan} ta` + (d.xatolar && d.xatolar.length ? `\nXatolar:\n${d.xatolar.join('\n')}` : ''));
    await sudXarajatlarBoliminiChizish();
  });
  body.querySelectorAll('[data-act="sx-mib-ochish"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const ishRaqami = prompt("MIB ijro ish raqamini kiriting:");
      if (!ishRaqami) return;
      await fetch(`${API_BASE}/sud/xarajatlar/${btn.dataset.id}/mib_ochish`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mib_ijro_ish_raqami: ishRaqami }),
      });
      await sudXarajatlarBoliminiChizish();
    });
  });
}

async function sudKiritilmaganBoliminiChizish() {
  try {
    const body = document.getElementById('sud-body');
    body.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;
    const data = await apiGet('/sud/kiritilmagan_royxat');
    body.innerHTML = `
      <div class="page-sub">Sudga topshirilmagan (sabab bilan) deb belgilangan ishlar. Belgilangan muddat o'tib, qarz hamon yopilmagan bo'lsa, "Amal" ustunida tavsiya ko'rinadi.</div>
      <div class="toolbar">
        <button class="btn" id="sk-excel">📊 Excel'ga eksport qilish</button>
      </div>
      <div class="table-wrap">
        <div class="table-scroll">
          <table>
            <thead><tr><th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Sababi</th><th>Sana</th><th>Izoh</th><th></th></tr></thead>
            <tbody>
              ${data.royxat.map(r => `<tr>
                <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td>
                <td>${r.sababi_nomi}</td><td>${r.sana}</td>
                <td>${r.xodim_ism ? `${r.xodim_ism} — ${r.izoh || ''}` : (r.izoh || '—')}</td>
                <td>
                  ${r.mijoz_arizasi_pdf ? `<a href="#" data-fayl="${r.mijoz_arizasi_pdf}" data-act="fayl-ochish">📄 Ariza</a>` : ''}
                  <button class="btn" data-anketa="${r.anketa_raqami}" data-act="sk-ortga" style="margin-left:6px;">↩ Ortga qaytarish</button>
                  <button class="btn danger" data-anketa="${r.anketa_raqami}" data-act="sk-nollash" style="margin-left:6px;">🗑 Nollashtirish</button>
                </td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
    document.getElementById('sk-excel').addEventListener('click', () => {
      window.open(`${API_BASE}/sud/kiritilmagan_excel`, '_blank');
    });
    body.querySelectorAll('[data-act="fayl-ochish"]').forEach(a => {
      a.addEventListener('click', (e) => { e.preventDefault(); window.open(`${API_BASE}/fayl_korish?yol=${encodeURIComponent(a.dataset.fayl)}`, '_blank'); });
    });
    body.querySelectorAll('[data-act="sk-nollash"]').forEach(btn => {
      btn.addEventListener('click', () => mibNollashDialogOchish(btn.dataset.anketa));
    });
    body.querySelectorAll('[data-act="sk-ortga"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm(`Anketa ${btn.dataset.anketa} uchun 'Sudga kiritilmadi' belgisini bekor qilib, ishni qayta 'Sudga topshirish kerak' navbatiga qaytarasizmi?`)) return;
        const r = await fetch(`${API_BASE}/sud/kiritilmadi_bekor_qilish`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ anketa_raqami: btn.dataset.anketa }),
        });
        const res = await r.json();
        if (res.xato) { alert('Xato: ' + res.xato); return; }
        await sudKiritilmaganBoliminiChizish();
      });
    });
  } catch (e) {
    const xatoJoy = document.getElementById('sud-body') || document.getElementById('main-content');
    if (xatoJoy) xatoJoy.innerHTML = `<div class="page-sub" style="color:var(--err);">Xato yuz berdi: ${e.message}</div>`;
  }
}

async function sudHisobotBoliminiChizish() {
  try {
    const body = document.getElementById('sud-body');
    body.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;
    const data = await apiGet('/davo-ariza/hisobot');
    body.innerHTML = `
      <div class="page-sub">Barcha tayyorlangan Davo arizalar — qachon yaratilgani, qancha vaqtda olib kelingani, ish raqami va mijoz qarzdorligi.</div>
      <div class="toolbar">
        <button class="btn" id="sh-excel">📊 Excel'ga eksport qilish</button>
      </div>
      <div class="table-wrap">
        <div class="table-scroll">
          <table>
            <thead><tr>
              <th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Qarzdorlik</th><th>Ariza yaratilgan</th>
              <th>Necha kun kutildi</th><th>Palata ish raqami</th><th>Palatadan kelgan</th><th>Holati</th>
              <th>Sud ish raqami</th><th>Sudga topshirilgan</th><th>Sud holati</th><th>Joriy bosqich</th>
            </tr></thead>
            <tbody>
              ${data.royxat.map(r => `<tr>
                <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.mijoz_turi}</td>
                <td>${formatSum(r.jami_qarz)}</td><td>${r.yaratilgan}</td><td>${r.kutilgan_kun}</td>
                <td>${r.ish_raqami}</td><td>${r.imzo_sana}</td><td>${davoHolatPill(r.holat_pill, r.holati)}</td>
                <td>${r.sud_ish_raqami}</td><td>${r.sud_sana}</td><td>${r.sud_holati}</td>
                <td style="font-weight:600;">${r.joriy_bosqich}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
    document.getElementById('sh-excel').addEventListener('click', () => {
      window.open(`${API_BASE}/davo-ariza/hisobot_excel`, '_blank');
    });
  } catch (e) {
    const xatoJoy = document.querySelector('#mib-body, #sud-body, #tn-body') || document.getElementById('main-content');
    if (xatoJoy) xatoJoy.innerHTML = `<div class="page-sub" style="color:var(--err);">Xato yuz berdi: ${e.message}</div>`;
  }

}

async function sudTopshirishBoliminiChizish() {
  try {
    const body = document.getElementById('sud-body');
    body.innerHTML = `
      <div class="toolbar">
        <input class="tb-input" id="sud-qidiruv" placeholder="Anketa raqami" style="width:130px;">
        <button class="btn" id="sud-qidirish-btn">🔍 Topish</button>
        <button class="btn" id="sud-refresh">🔄 Yangilash</button>
        <button class="btn" id="sud-select-all">☑ Hammasi</button>
        <button class="btn" id="sud-select-none">☐ Bekor qilish</button>
        <span class="badge-count" id="sud-count">Belgilangan: 0 ta</span>
        ${ochiladiganMenyu('sud-amallar-dd', '✓ Amallar', `
          <button class="btn" id="sud-manual-mark" style="display:block; width:100%; text-align:left; margin-bottom:4px;">✓ Sudga topshirildi deb belgilash</button>
          <button class="btn danger" id="sud-kiritilmadi-btn" style="display:block; width:100%; text-align:left;">✕ Sudga kiritilmadi (sabab bilan)</button>
        `)}
        <button class="btn" id="sud-shablon">📤 Shablon</button>
        <button class="btn-gold" id="sud-export" style="margin-left:0;">📊 Excelga eksport</button>
        <button class="btn-gold" id="sud-import" style="margin-left:0;">📥 To'ldirilgan Excel</button>
        <input type="file" id="sud-file-input" accept=".xlsx,.xls" style="display:none;">
        <button class="btn-gold" id="sud-eski-ish" style="margin-left:0;">📁 Eski sud ishini kiritish</button>
      </div>
      <div class="table-wrap">
        <div class="table-scroll">
          <table>
            <thead><tr>
              <th></th><th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Sud turi</th>
              <th>Jami qarzdorlik</th><th>Palatadan kelgan sana</th><th>Yig'ma jild</th><th>Ruxsat</th>
            </tr></thead>
            <tbody id="sud-tbody"></tbody>
          </table>
        </div>
      </div>
    `;
    document.getElementById('sud-refresh').addEventListener('click', sudTopshirishRoyxatniYangilash);
    document.getElementById('sud-select-all').addEventListener('click', () => {
      sudTopshirishCache.forEach(r => sudBelgilangan.add(r.anketa_raqami));
      sudTopshirishJadvalniChizish();
    });
    document.getElementById('sud-select-none').addEventListener('click', () => {
      sudBelgilangan.clear();
      sudTopshirishJadvalniChizish();
    });
    document.getElementById('sud-tbody').addEventListener('click', (e) => {
      const el = e.target.closest('.checkbox');
      if (!el) return;
      const anketa = el.dataset.anketa;
      if (sudBelgilangan.has(anketa)) { sudBelgilangan.delete(anketa); el.classList.remove('checked'); }
      else { sudBelgilangan.add(anketa); el.classList.add('checked'); }
      document.getElementById('sud-count').textContent = `Belgilangan: ${sudBelgilangan.size} ta`;
    });

    ochiladiganMenyuIshga('sud-amallar-dd');
    document.getElementById('sud-manual-mark').addEventListener('click', () => {
      if (sudBelgilangan.size !== 1) { alert('Aynan bitta mijozni belgilang.'); return; }
      const anketa = Array.from(sudBelgilangan)[0];
      const overlay = document.createElement('div');
      overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
      overlay.innerHTML = `
        <div style="background:#fff;border-radius:12px;padding:20px 24px;width:400px;">
          <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Sudga topshirildi — ${anketa}</div>
          <label style="display:block;margin-bottom:8px;">Sud ish raqami<br><input class="tb-input" id="sm-ish" style="width:100%;"></label>
          <label style="display:block;margin-bottom:8px;">Sana (kun.oy.yil)<br><input class="tb-input" id="sm-sana" style="width:100%;"></label>
          <label style="display:block;margin-bottom:8px;">Sud buyrug'i (agar mavjud bo'lsa, PDF)<br>
            <input type="file" id="sm-fayl" accept=".pdf" style="width:100%; margin-top:4px;"></label>
          <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
            <button class="btn" id="sm-cancel">Bekor qilish</button>
            <button class="btn-gold" id="sm-save" style="margin-left:0;">✓ Saqlash</button>
          </div>
        </div>`;
      document.body.appendChild(overlay);
      document.getElementById('sm-cancel').addEventListener('click', () => overlay.remove());
      document.getElementById('sm-save').addEventListener('click', async () => {
        const ish = document.getElementById('sm-ish').value.trim();
        const sana = document.getElementById('sm-sana').value.trim();
        const fayl = document.getElementById('sm-fayl').files[0];
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
        await sudTopshirishRoyxatniYangilash();
      });
    });

    document.getElementById('sud-export').addEventListener('click', () => {
      tayyorJildYuklabOlish(`${API_BASE}/sud/topshirish_kerak_excel`);
    });
    document.getElementById('sud-shablon').addEventListener('click', async () => {
      if (sudBelgilangan.size === 0) { alert('Kamida bitta mijozni belgilang.'); return; }
      await davoFileDownloadPost('/sud/topshirish_shablon', { anketalar: Array.from(sudBelgilangan) }, 'sudga_topshirish_shabloni.xlsx');
    });
    document.getElementById('sud-import').addEventListener('click', () => document.getElementById('sud-file-input').click());
    document.getElementById('sud-file-input').addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${API_BASE}/sud/topshirish_excel_import`, { method: 'POST', body: fd });
      const data = await r.json();
      if (data.xato) { alert('Xato: ' + data.xato); return; }
      alert(`${data.yangilandi} ta mijoz 'Sudga topshirildi' deb belgilandi.\n${data.otkazib_yuborildi} ta o'tkazib yuborildi.\n${data.topilmadi} ta topilmadi.`);
      e.target.value = '';
      await sudTopshirishRoyxatniYangilash();
    });

    document.getElementById('sud-qidirish-btn').addEventListener('click', async () => {
      const anketa = document.getElementById('sud-qidiruv').value.trim();
      if (!anketa) return;
      const res = await apiGet(`/sud/qidirish?anketa=${encodeURIComponent(anketa)}`);
      if (!res.topildi) { alert("Bu anketa 'Sudga topshirish kerak' ro'yxatida topilmadi."); return; }
      sudTopshirishCache = [res.row];
      sudBelgilangan.clear();
      sudTopshirishJadvalniChizish();
    });
    document.getElementById('sud-eski-ish').addEventListener('click', sudEskiIshDialogOchish);
    document.getElementById('sud-kiritilmadi-btn').addEventListener('click', sudKiritilmadiDialogOchish);

    await sudTopshirishRoyxatniYangilash();
  } catch (e) {
    const xatoJoy = document.querySelector('#mib-body, #sud-body, #tn-body') || document.getElementById('main-content');
    if (xatoJoy) xatoJoy.innerHTML = `<div class="page-sub" style="color:var(--err);">Xato yuz berdi: ${e.message}</div>`;
  }

}

function sudKiritilmadiDialogOchish() {
  if (sudBelgilangan.size !== 1) { alert("Aynan bitta mijozni belgilang."); return; }
  const anketa = Array.from(sudBelgilangan)[0];
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:440px;max-height:85vh;overflow-y:auto;">
      <div style="font-size:16px;font-weight:700;margin-bottom:6px;">Sudga kiritilmadi — ${anketa}</div>
      <div class="page-sub" style="margin:0 0 14px;">Tasdiqlangan Davo ariza nima sababdan sudga topshirilmayotganini belgilang.</div>

      <label style="display:block;margin-bottom:10px;">Sabab turi<br>
        <select class="tb-select" id="sk-sababi" style="width:100%; margin-top:4px;">
          <option value="">— tanlang —</option>
          <option value="qarz_yopilgan">Qarz to'liq yopilgan</option>
          <option value="mijoz_arizasi">Mijozning yozma arizasi asosida</option>
          <option value="xodim_iltimosi">Bank xodimi iltimosiga asosan</option>
        </select>
      </label>

      <div id="sk-qarz-info" style="display:none; font-size:12px; color:var(--muted); background:#F4F6FB; border-radius:8px; padding:10px; margin-bottom:10px;">
        Diqqat: bu sabab tizim tomonidan tekshiriladi. Agar portfelda hali qarzdorlik ko'rinsa, rad etiladi.
      </div>

      <div id="sk-mijoz-arizasi-blok" style="display:none;">
        <label style="display:block;margin-bottom:10px;">Mijozning yozma arizasi (PDF) — <b style="color:var(--err);">majburiy</b><br>
          <input type="file" id="sk-mijoz-pdf" accept=".pdf" style="width:100%; margin-top:4px;"></label>
      </div>

      <div id="sk-xodim-blok" style="display:none;">
        <label style="display:block;margin-bottom:10px;">Bank xodimi F.I.Sh<br>
          <input class="tb-input" id="sk-xodim-ism" style="width:100%;"></label>
        <label style="display:block;margin-bottom:10px;">Qoldirish sababi<br>
          <select class="tb-select" id="sk-izoh-tanlov" style="width:100%; margin-bottom:6px;">
            <option value="">— tayyor variantlardan tanlang (ixtiyoriy) —</option>
            <option value="Mijoz tanishi">Mijoz tanishi</option>
            <option value="Mijoz pulini ishlatib qo'ygani sababli">Mijoz pulini ishlatib qo'ygani sababli</option>
            <option value="Mijoz iltimos qilganligi sababli">Mijoz iltimos qilganligi sababli</option>
          </select>
          <textarea class="tb-input" id="sk-izoh" style="width:100%;" rows="2" placeholder="To'liq izoh yozing yoki yuqoridan tanlang"></textarea>
        </label>
      </div>

      <label style="display:block;margin-bottom:10px;">Sana (kun.oy.yil)<br>
        <input class="tb-input" id="sk-sana" style="width:100%;"></label>

      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="sk-cancel">Bekor qilish</button>
        <button class="btn-gold" id="sk-save" style="margin-left:0;">✓ Saqlash</button>
      </div>
    </div>`);

  const sababiSelect = overlay.querySelector('#sk-sababi');
  sababiSelect.addEventListener('change', () => {
    const v = sababiSelect.value;
    overlay.querySelector('#sk-qarz-info').style.display = v === 'qarz_yopilgan' ? 'block' : 'none';
    overlay.querySelector('#sk-mijoz-arizasi-blok').style.display = v === 'mijoz_arizasi' ? 'block' : 'none';
    overlay.querySelector('#sk-xodim-blok').style.display = v === 'xodim_iltimosi' ? 'block' : 'none';
  });
  overlay.querySelector('#sk-izoh-tanlov').addEventListener('change', (e) => {
    if (e.target.value) overlay.querySelector('#sk-izoh').value = e.target.value;
  });

  overlay.querySelector('#sk-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#sk-save').addEventListener('click', async () => {
    const sababi = sababiSelect.value;
    const sana = overlay.querySelector('#sk-sana').value.trim();
    if (!sababi) { alert('Sabab turini tanlang.'); return; }
    if (!sana) { alert('Sanani kiriting.'); return; }

    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('sababi', sababi);
    fd.append('sana', sana);

    if (sababi === 'mijoz_arizasi') {
      const pdfFile = overlay.querySelector('#sk-mijoz-pdf').files[0];
      if (!pdfFile) { alert("Mijozning yozma arizasi (PDF) yuklash majburiy."); return; }
      fd.append('mijoz_arizasi_pdf', pdfFile);
    } else if (sababi === 'xodim_iltimosi') {
      const ism = overlay.querySelector('#sk-xodim-ism').value.trim();
      const izoh = overlay.querySelector('#sk-izoh').value.trim();
      if (!ism) { alert("Bank xodimining F.I.Sh kiriting."); return; }
      if (!izoh) { alert("Qoldirish sababini kiriting."); return; }
      fd.append('xodim_ism', ism);
      fd.append('izoh', izoh);
    }

    const r = await fetch(`${API_BASE}/sud/kiritilmadi`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    await sudTopshirishRoyxatniYangilash();
  });
}

function sudEskiIshDialogOchish() {
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:420px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:6px;">Eski sud ishini kiritish</div>
      <div class="page-sub" style="margin:0 0 12px;">Bu dasturdan tashqarida avvalroq sudga topshirilgan ish uchun.</div>
      <label style="display:block;margin-bottom:8px;">Anketa raqami<br>
        <div style="display:flex; gap:6px;">
          <input class="tb-input" id="se-anketa" style="flex:1;">
          <button class="btn" id="se-qidirish">🔍 Topish</button>
        </div></label>
      <div id="se-natija" style="font-size:12.5px; color:var(--muted); margin-bottom:10px;">Hali qidirilmagan</div>
      <label style="display:block;margin-bottom:8px;">Sud ish raqami<br><input class="tb-input" id="se-ish" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Sud sanasi<br><input class="tb-input" id="se-sana" style="width:100%;"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="se-cancel">Bekor qilish</button>
        <button class="btn-gold" id="se-save" style="margin-left:0;">✓ Kiritish</button>
      </div>
    </div>`);
  overlay.querySelector('#se-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#se-qidirish').addEventListener('click', async () => {
    const anketa = overlay.querySelector('#se-anketa').value.trim();
    if (!anketa) return;
    const data = await apiGet(`/sud/eski_ish_qidirish?anketa=${encodeURIComponent(anketa)}`);
    if (!data.topildi) { overlay.querySelector('#se-natija').textContent = "Bu anketa portfelda topilmadi."; return; }
    let msg = `Topildi: ${data.mijoz_nomi} (${data.turi}), qarzdorlik: ${formatSum(data.jami_qarz)}`;
    if (data.mavjud_yozuv_bor) msg += " ⚠ Diqqat: bu mijoz uchun bazada allaqachon yozuv bor.";
    overlay.querySelector('#se-natija').textContent = msg;
  });
  overlay.querySelector('#se-save').addEventListener('click', async () => {
    const anketa = overlay.querySelector('#se-anketa').value.trim();
    const ish = overlay.querySelector('#se-ish').value.trim();
    const sana = overlay.querySelector('#se-sana').value.trim();
    if (!anketa || !ish || !sana) { alert('Anketa, ish raqami va sanani kiriting.'); return; }
    const r = await fetch(`${API_BASE}/sud/eski_ish_kiritish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anketa_raqami: anketa, ish_raqami: ish, sana }),
    });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    await ekranniOchish('sud');
  });
}

async function sudTopshirishRoyxatniYangilash() {
  const data = await apiGet('/sud/topshirish_kerak');
  sudTopshirishCache = data.royxat;
  sudBelgilangan.clear();
  sudTopshirishJadvalniChizish();
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
        else window.open(`${API_BASE}/mib/tayyor_jild?anketa=${encodeURIComponent(anketa)}`, '_blank');
      });
    });
  });
}

function sudTopshirishJadvalniChizish() {
  const tbody = document.getElementById('sud-tbody');
  tbody.innerHTML = sudTopshirishCache.map(r => {
    const checked = sudBelgilangan.has(r.anketa_raqami);
    return `<tr>
      <td><span class="checkbox ${checked ? 'checked' : ''}" data-anketa="${r.anketa_raqami}"></span></td>
      <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td><td>${r.sud_nomi}</td>
      <td>${formatSum(r.jami)}</td><td>${r.imzo_sana || '—'}</td>
      <td>
        ${r.yigma_jild_bor
          ? `<a href="#" data-anketa="${r.anketa_raqami}" data-act="sud-jild-korish" style="font-weight:600;">📁 Ko'rish</a>`
          : `<button class="btn-gold" data-anketa="${r.anketa_raqami}" data-act="sud-jild-shakillantir" style="padding:4px 10px; font-size:11.5px; margin-left:0;">⚙ Shakillantirish</button>`}
      </td>
      <td>${r.ruxsat_berilgan ? '<span style="color:#1E6B2E; font-weight:600;">✓ Berilgan</span>' : '<span style="color:var(--muted);">— Yo\'q</span>'}</td>
    </tr>`;
  }).join('');
  document.getElementById('sud-count').textContent = `Belgilangan: ${sudBelgilangan.size} ta`;
  tbody.querySelectorAll('[data-act="sud-jild-korish"]').forEach(a => {
    a.addEventListener('click', (e) => { e.preventDefault(); sudYigmaJildDialogOchish(a.dataset.anketa); });
  });
  tbody.querySelectorAll('[data-act="sud-jild-shakillantir"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const r = await fetch(`${API_BASE}/sud/yigma_jild_yaratish`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anketa_raqami: btn.dataset.anketa }),
      });
      const d = await r.json();
      if (d.xato) { alert('Xato: ' + d.xato); return; }
      // MUHIM: jild muvaffaqiyatli yaratilgach, avval asosiy JADVALNI
      // (bu tugma "Shakillantirish"dan "Ko'rish"ga o'zgarishi uchun)
      // yangilaymiz, so'ng hujjatlar oynasini ochamiz. Aks holda, jild
      // aslida yaratilgan bo'lsa ham, jadval eski ("Shakillantirish")
      // holatni ko'rsatib qolaverar edi.
      await sudTopshirishRoyxatniYangilash();
      sudYigmaJildDialogOchish(btn.dataset.anketa);
    });
  });
}

async function sudRoyxatBoliminiChizish() {
  const body = document.getElementById('sud-body');
  body.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;
  const data = await apiGet('/sud/royxat');
  sudRoyxatCache = data.royxat;
  body.innerHTML = `
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Jami sud summasi</th>
            <th>Sud ish raqami</th><th>Sudga topshirilgan</th><th>MIB holati</th>
          </tr></thead>
          <tbody>
            ${sudRoyxatCache.map(r => `<tr>
              <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td>
              <td>${formatSum(r.jami_sud_summasi)}</td><td>${r.sud_ish_raqami}</td>
              <td>${r.sudga_topshirilgan}</td>
              <td>${davoHolatPill(r.mib_holati.startsWith('✓') ? 'olib_kelindi' : 'tayyor', r.mib_holati)}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// ---------------- MIB IJRO HARAKATLARI ----------------
let mibSubTab = 'otkazish';

async function mibIjroniYuklash(main) {
  main.innerHTML = `
    <div class="page-title">MIB (Ijro byurosi) bazasi</div>
    <div class="page-sub">Sudga topshirilgan hujjatlarni MIBga o'tkazishni tasdiqlaysiz, so'ng undirish jarayonidagi harakatlarni shu yerda kuzatib borasiz.</div>
    <div style="display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap;">
      <button class="btn" id="mib-tab-otkazish" style="${mibSubTab === 'otkazish' ? 'background:var(--navy);color:#fff;' : ''}">MIBga o'tkazish kerak</button>
      <button class="btn" id="mib-tab-faol" style="${mibSubTab === 'faol' ? 'background:var(--navy);color:#fff;' : ''}">Jarayondagi hujjatlar</button>
      <button class="btn" id="mib-tab-harakatsiz" style="${mibSubTab === 'harakatsiz' ? 'background:var(--navy);color:#fff;' : ''}">Harakatsiz qolganlar</button>
      <button class="btn" id="mib-tab-yakunlangan" style="${mibSubTab === 'yakunlangan' ? 'background:var(--navy);color:#fff;' : ''}">Yakunlangan ishlar</button>
      <button class="btn" id="mib-tab-tolovlar" style="${mibSubTab === 'tolovlar' ? 'background:var(--navy);color:#fff;' : ''}">💰 To'lovlar</button>
    </div>
    <div id="mib-body"></div>
  `;
  document.getElementById('mib-tab-otkazish').addEventListener('click', () => { mibSubTab = 'otkazish'; mibIjroniYuklash(main); });
  document.getElementById('mib-tab-faol').addEventListener('click', () => { mibSubTab = 'faol'; mibIjroniYuklash(main); });
  document.getElementById('mib-tab-harakatsiz').addEventListener('click', () => { mibSubTab = 'harakatsiz'; mibIjroniYuklash(main); });
  document.getElementById('mib-tab-yakunlangan').addEventListener('click', () => { mibSubTab = 'yakunlangan'; mibIjroniYuklash(main); });
  document.getElementById('mib-tab-tolovlar').addEventListener('click', () => { mibSubTab = 'tolovlar'; mibIjroniYuklash(main); });

  if (mibSubTab === 'otkazish') await mibOtkazishChizish();
  else if (mibSubTab === 'faol') await mibFaolChizish();
  else if (mibSubTab === 'harakatsiz') await mibHarakatsizChizish();
  else if (mibSubTab === 'yakunlangan') await mibYakunlanganChizish();
  else await mibTolovlarChizish();
}

async function mibTolovlarChizish() {
  const body = document.getElementById('mib-body');
  body.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;

  const [kunlik, mibTolov] = await Promise.all([
    apiGet('/mib/tolovlar_royxat?manba=kunlik_29801'),
    apiGet('/mib/tolovlar_royxat?manba=mib'),
  ]);

  const holatPillRender = (h) => {
    const map = { tasdiqlangan: ['olib_kelindi', '✓ Tasdiqlangan'], aniqlash_kerak: ['tayyor', '⚠ Aniqlash kerak'],
                  mos_kelmadi: ['otgan', "✕ Mos kelmadi"] };
    const [pill, matn] = map[h] || ['yoq', h];
    return davoHolatPill(pill, matn);
  };

  const jadvalChiz = (royxat, prefiks) => `
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr><th>Sana</th><th>PINFL/STIR</th><th>F.I.Sh</th><th>Summa</th><th>Anketa</th><th>Mijoz</th><th>Holati</th><th></th></tr></thead>
          <tbody>
            ${royxat.map(t => `<tr>
              <td>${t.sana}</td><td>${t.pinfl_yoki_stir}</td><td>${t.toliq_ism || '—'}</td>
              <td>${formatSum(t.summa)}</td><td>${t.anketa_raqami || '—'}</td><td>${t.mijoz_nomi || '—'}</td>
              <td>${holatPillRender(t.holati)}</td>
              <td>
                ${t.holati === 'aniqlash_kerak' ? `<button class="btn" data-id="${t.id}" data-pinfl="${t.pinfl_yoki_stir}" data-act="tanlash">Anketa tanlash</button>` : ''}
                ${t.holati === 'mos_kelmadi' ? `<button class="btn" data-id="${t.id}" data-act="qidirish">🔍 Qidirib biriktirish</button>` : ''}
              </td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>`;

  body.innerHTML = `
    <div class="card-row">
      <div class="card" style="flex:1;">
        <div class="card-h">Kunlik to'lovlar (29801-hisobvaraq)</div>
        <div class="btn-row">
          <button class="btn" id="tk-shablon">📤 Shablon yuklab olish</button>
          <button class="btn-gold" id="tk-import-btn" style="margin-left:0;">📥 Excel yuklash</button>
          <input type="file" id="tk-file" accept=".xlsx,.xls" style="display:none;">
        </div>
      </div>
      <div class="card" style="flex:1;">
        <div class="card-h">MIBdan kelgan to'lovlar</div>
        <div class="btn-row">
          <button class="btn" id="tm-shablon">📤 Shablon yuklab olish</button>
          <button class="btn-gold" id="tm-import-btn" style="margin-left:0;">📥 Excel yuklash</button>
          <input type="file" id="tm-file" accept=".xlsx,.xls" style="display:none;">
        </div>
      </div>
    </div>

    <div class="card-h" style="margin-bottom:10px;">Kunlik to'lovlar ro'yxati (${kunlik.royxat.length} ta)</div>
    ${jadvalChiz(kunlik.royxat, 'tk')}

    <div class="card-h" style="margin:20px 0 10px;">MIBdan kelgan to'lovlar ro'yxati (${mibTolov.royxat.length} ta)</div>
    ${jadvalChiz(mibTolov.royxat, 'tm')}
  `;

  document.getElementById('tk-shablon').addEventListener('click', () => {
    window.open(`${API_BASE}/mib/tolovlar_shablon?manba=kunlik_29801`, '_blank');
  });
  document.getElementById('tm-shablon').addEventListener('click', () => {
    window.open(`${API_BASE}/mib/tolovlar_shablon?manba=mib`, '_blank');
  });
  document.getElementById('tk-import-btn').addEventListener('click', () => document.getElementById('tk-file').click());
  document.getElementById('tm-import-btn').addEventListener('click', () => document.getElementById('tm-file').click());

  const importQilish = async (fileInputId, manba) => {
    const f = document.getElementById(fileInputId).files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append('file', f);
    fd.append('manba', manba);
    const r = await fetch(`${API_BASE}/mib/tolovlar_import`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    let msg = `✓ Tasdiqlangan: ${data.tasdiqlangan} ta\n⚠ Anketa aniqlash kerak: ${data.aniqlash_kerak} ta\n✕ Mos kelmadi: ${data.mos_kelmadi} ta`;
    if (data.dublikat) msg += `\n⏭ Dublikat (o'tkazib yuborildi): ${data.dublikat} ta`;
    if (data.xatolar && data.xatolar.length) msg += `\n\nXatolar:\n${data.xatolar.slice(0, 5).join('\n')}`;
    alert(msg);
    document.getElementById(fileInputId).value = '';
    await mibIjroniYuklash(document.getElementById('main-content'));
  };
  document.getElementById('tk-file').addEventListener('change', () => importQilish('tk-file', 'kunlik_29801'));
  document.getElementById('tm-file').addEventListener('change', () => importQilish('tm-file', 'mib'));

  body.querySelectorAll('[data-act="tanlash"]').forEach(btn => {
    btn.addEventListener('click', () => tolovAnketaTanlashDialog(btn.dataset.id, btn.dataset.pinfl));
  });
  body.querySelectorAll('[data-act="qidirish"]').forEach(btn => {
    btn.addEventListener('click', () => tolovQidirishDialog(btn.dataset.id));
  });
}

async function tolovQidirishDialog(tolovId) {
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:460px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:6px;">Qo'lda qidirib biriktirish</div>
      <div class="page-sub" style="margin:0 0 12px;">Avtomatik aniqlash ishlamadi. Anketa raqami yoki mijoz nomi bo'yicha qidiring.</div>
      <div class="btn-row" style="margin-bottom:12px;">
        <input class="tb-input" id="tq-qidiruv" placeholder="Anketa raqami yoki mijoz nomi..." style="flex:1;">
        <button class="btn-gold" id="tq-qidirish-btn" style="margin-left:0;">🔍 Qidirish</button>
      </div>
      <div id="tq-natijalar"></div>
      <div style="display:flex; justify-content:flex-end; margin-top:10px;">
        <button class="btn" id="tq-yopish">Yopish</button>
      </div>
    </div>`);
  overlay.querySelector('#tq-yopish').addEventListener('click', () => overlay.remove());
  const qidirish = async () => {
    const q = overlay.querySelector('#tq-qidiruv').value.trim();
    if (!q) return;
    const data = await apiGet(`/mib/tolov_qidirish?q=${encodeURIComponent(q)}`);
    const div = overlay.querySelector('#tq-natijalar');
    if (data.natija.length === 0) {
      div.innerHTML = '<div class="page-sub">Hech narsa topilmadi.</div>';
      return;
    }
    div.innerHTML = data.natija.map(n => `
      <div class="card" style="margin-bottom:8px; cursor:pointer;" data-anketa="${n.anketa_raqami}">
        <div style="font-weight:600;">${n.anketa_raqami} — ${n.mijoz_nomi}</div>
        <div style="font-size:12px; color:var(--muted);">Qarzdorlik: ${formatSum(n.jami_qarz)}</div>
      </div>`).join('');
    div.querySelectorAll('[data-anketa]').forEach(card => {
      card.addEventListener('click', async () => {
        const r = await fetch(`${API_BASE}/mib/tolov_anketa_tanlash`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tolov_id: tolovId, anketa_raqami: card.dataset.anketa }),
        });
        const res = await r.json();
        if (res.xato) { alert('Xato: ' + res.xato); return; }
        overlay.remove();
        await mibIjroniYuklash(document.getElementById('main-content'));
      });
    });
  };
  overlay.querySelector('#tq-qidirish-btn').addEventListener('click', qidirish);
  overlay.querySelector('#tq-qidiruv').addEventListener('keydown', (e) => { if (e.key === 'Enter') qidirish(); });
}

async function tolovAnketaTanlashDialog(tolovId, pinfl) {
  const data = await apiGet(`/mib/tolov_nomzodlar?pinfl=${encodeURIComponent(pinfl)}`);
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:460px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:6px;">Qaysi anketaga tegishli?</div>
      <div class="page-sub" style="margin:0 0 14px;">PINFL/STIR: ${pinfl} — ${data.nomzodlar.length} ta anketa topildi.</div>
      ${data.nomzodlar.map(n => `
        <div class="card" style="margin-bottom:8px; cursor:pointer;" data-anketa="${n.anketa_raqami}">
          <div style="font-weight:600;">${n.anketa_raqami} — ${n.mijoz_nomi}</div>
          <div style="font-size:12px; color:var(--muted);">Qarzdorlik: ${formatSum(n.jami_qarz)}</div>
        </div>
      `).join('')}
      <div style="display:flex; justify-content:flex-end; margin-top:10px;">
        <button class="btn" id="ta-yopish">Bekor qilish</button>
      </div>
    </div>`);
  overlay.querySelector('#ta-yopish').addEventListener('click', () => overlay.remove());
  overlay.querySelectorAll('[data-anketa]').forEach(card => {
    card.addEventListener('click', async () => {
      const r = await fetch(`${API_BASE}/mib/tolov_anketa_tanlash`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tolov_id: tolovId, anketa_raqami: card.dataset.anketa }),
      });
      const res = await r.json();
      if (res.xato) { alert('Xato: ' + res.xato); return; }
      overlay.remove();
      await mibIjroniYuklash(document.getElementById('main-content'));
    });
  });
}

async function mibHarakatsizChizish() {
  try {
    const body = document.getElementById('mib-body');
    body.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;
    const data = await apiGet('/mib/harakatsizlar');
    body.innerHTML = `
      <div class="page-sub">MIBga o'tkazilgandan (yoki oxirgi harakatdan) keyin belgilangan muddat ichida hech qanday yangi harakat qayd qilinmagan mijozlar.</div>
      <div class="toolbar">
        <button class="btn" id="mib-harakatsiz-excel">📊 Excel'ga eksport qilish</button>
      </div>
      <div class="table-wrap">
        <div class="table-scroll">
          <table>
            <thead><tr><th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Qarzdorlik</th><th>MIB ish raqami</th><th>Necha kun harakatsiz</th></tr></thead>
            <tbody>
              ${data.royxat.map(r => `<tr style="background:var(--pill-red-bg);">
                <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td>
                <td>${formatSum(r.jami_qarz)}</td><td>${r.mib_ish_raqami}</td><td>${r.harakatsizlik_kun}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
    document.getElementById('mib-harakatsiz-excel').addEventListener('click', () => {
      window.open(`${API_BASE}/mib/harakatsizlar_excel`, '_blank');
    });
  } catch (e) {
    const xatoJoy = document.querySelector('#mib-body, #sud-body, #tn-body') || document.getElementById('main-content');
    if (xatoJoy) xatoJoy.innerHTML = `<div class="page-sub" style="color:var(--err);">Xato yuz berdi: ${e.message}</div>`;
  }

}

async function mibOtkazishChizish() {
  try {
    const body = document.getElementById('mib-body');
    const data = await apiGet('/mib/otkazish_kerak');
    window._mibOtkazishCache = data.royxat;
    body.innerHTML = `
      <div class="toolbar">
        <input class="tb-input" id="mo-qidiruv" placeholder="Anketa raqami" style="width:160px;">
        <button class="btn" id="mo-qidirish-btn">🔍 Topish</button>
        <button class="btn" id="mo-tozalash-btn">✕ Tozalash</button>
        <button class="btn" id="mib-otkazish-excel" style="margin-left:auto;">📊 Excel'ga eksport qilish</button>
      </div>
      <div id="mo-jadval-wrap"></div>
    `;
    mibOtkazishJadvalniChizish(data.royxat);

    document.getElementById('mo-qidirish-btn').addEventListener('click', () => {
      const q = document.getElementById('mo-qidiruv').value.trim();
      if (!q) { mibOtkazishJadvalniChizish(window._mibOtkazishCache); return; }
      const filtrlangan = window._mibOtkazishCache.filter(r => r.anketa_raqami.includes(q));
      mibOtkazishJadvalniChizish(filtrlangan);
    });
    document.getElementById('mo-qidiruv').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') document.getElementById('mo-qidirish-btn').click();
    });
    document.getElementById('mo-tozalash-btn').addEventListener('click', () => {
      document.getElementById('mo-qidiruv').value = '';
      mibOtkazishJadvalniChizish(window._mibOtkazishCache);
    });
    document.getElementById('mib-otkazish-excel').addEventListener('click', () => {
      window.open(`${API_BASE}/mib/otkazish_kerak_excel`, '_blank');
    });
  } catch (e) {
    const xatoJoy = document.querySelector('#mib-body, #sud-body, #tn-body') || document.getElementById('main-content');
    if (xatoJoy) xatoJoy.innerHTML = `<div class="page-sub" style="color:var(--err);">Xato yuz berdi: ${e.message}</div>`;
  }

}

function mibOtkazishJadvalniChizish(royxat) {
  const wrap = document.getElementById('mo-jadval-wrap');
  wrap.innerHTML = `
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Jami</th>
            <th>Sud ish raqami</th><th>Sudga topshirilgan</th><th></th>
          </tr></thead>
          <tbody>
            ${royxat.map(r => `<tr>
              <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td>
              <td>${formatSum(r.jami)}</td><td>${r.sud_ish_raqami}</td><td>${r.sudga_topshirilgan}</td>
              <td><button class="btn" data-anketa="${r.anketa_raqami}" data-sud-mavjud="${r.sud_buyrugi_mavjud}" data-act="mib-transfer">→ MIBga o'tkazildi</button></td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
  wrap.querySelectorAll('[data-act="mib-transfer"]').forEach(btn => {
    btn.addEventListener('click', () => mibTransferDialog(btn.dataset.anketa, btn.dataset.sudMavjud === 'true'));
  });
}

function mibTransferDialog(anketa, sudBuyrugiMavjud) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:440px;max-height:85vh;overflow-y:auto;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">MIBga o'tkazish — ${anketa}</div>
      ${sudBuyrugiMavjud
        ? `<div style="font-size:12.5px; color:var(--stamp); background:#F4F6FB; border-radius:8px; padding:8px 10px; margin-bottom:12px;">✓ Sud qarori avvalroq qayd etilgan — qayta so'ralmaydi.</div>`
        : `
        <label style="display:block;margin-bottom:8px;">Sud qarori natijasi<br>
          <select class="tb-select" id="mt-natija" style="width:100%;">
            <option value="bank_foydasiga">✓ Bank foydasiga</option>
            <option value="qisman">≈ Qisman</option>
            <option value="rad_etildi">✕ Rad etildi</option>
          </select></label>
        <div id="mt-qisman-fields" style="display:none;">
          <label style="display:block;margin-bottom:8px;">Asosiy qarz farqi<br><input class="tb-input" id="mt-qisman-asosiy" style="width:100%;" value="0"></label>
          <label style="display:block;margin-bottom:8px;">Foiz farqi<br><input class="tb-input" id="mt-qisman-foiz" style="width:100%;" value="0"></label>
          <label style="display:block;margin-bottom:8px;">Penya farqi<br><input class="tb-input" id="mt-qisman-penya" style="width:100%;" value="0"></label>
        </div>
        <div id="mt-rad-fields" style="display:none;">
          <label style="display:block;margin-bottom:8px;">Rad etilish sababi<br><textarea class="tb-input" id="mt-rad-sababi" style="width:100%; min-height:60px;"></textarea></label>
        </div>
        <label style="display:block;margin-bottom:8px;">Sud qarori (PDF) — <b style="color:var(--err);">majburiy</b><br>
          <input type="file" id="mt-sud-file" accept=".pdf" style="width:100%; margin-top:4px;"></label>
        `}
      <div id="mt-mib-fields">
        <label style="display:block;margin-bottom:8px;">MIB ish raqami<br><input class="tb-input" id="mt-ish" style="width:100%;"></label>
        <label style="display:block;margin-bottom:8px;">Sana (kun.oy.yil)<br><input class="tb-input" id="mt-sana" style="width:100%;"></label>
        <label style="display:block;margin-bottom:8px;">Ijro varaqasi (PDF) — <b style="color:var(--err);">majburiy</b><br>
          <input type="file" id="mt-file" accept=".pdf" style="width:100%; margin-top:4px;"></label>
      </div>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="mt-cancel">Bekor qilish</button>
        <button class="btn-gold" id="mt-save" style="margin-left:0;">✓ Saqlash</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  document.getElementById('mt-cancel').addEventListener('click', () => overlay.remove());

  const natijaSelect = document.getElementById('mt-natija');
  const mibFields = document.getElementById('mt-mib-fields');
  if (natijaSelect) {
    natijaSelect.addEventListener('change', () => {
      document.getElementById('mt-qisman-fields').style.display = natijaSelect.value === 'qisman' ? 'block' : 'none';
      document.getElementById('mt-rad-fields').style.display = natijaSelect.value === 'rad_etildi' ? 'block' : 'none';
      // MUHIM: "Rad etildi" tanlansa, MIBga o'tkazish maydonlari
      // (ish raqami, Ijro varaqasi) KERAK EMAS — chunki bu holatda
      // ish MIBga umuman o'tkazilmaydi.
      mibFields.style.display = natijaSelect.value === 'rad_etildi' ? 'none' : 'block';
    });
  }

  document.getElementById('mt-save').addEventListener('click', async () => {
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);

    let radEtildi = false;
    if (!sudBuyrugiMavjud) {
      const natija = natijaSelect.value;
      const sudFile = document.getElementById('mt-sud-file').files[0];
      if (!sudFile) { alert("Sud qarori (PDF) yuklash majburiy."); return; }
      fd.append('natija', natija);
      fd.append('qaror_fayl', sudFile);
      if (natija === 'qisman') {
        fd.append('qisman_asosiy_farq', document.getElementById('mt-qisman-asosiy').value);
        fd.append('qisman_foiz_farq', document.getElementById('mt-qisman-foiz').value);
        fd.append('qisman_penya_farq', document.getElementById('mt-qisman-penya').value);
      }
      if (natija === 'rad_etildi') {
        fd.append('rad_sababi', document.getElementById('mt-rad-sababi').value);
        radEtildi = true;
      }
    }

    if (!radEtildi) {
      const ish = document.getElementById('mt-ish').value.trim();
      const sana = document.getElementById('mt-sana').value.trim();
      const ijroFile = document.getElementById('mt-file').files[0];
      if (!ish || !sana) { alert('Ish raqami va sanani kiriting.'); return; }
      if (!ijroFile) { alert("Ijro varaqasi (PDF) yuklash majburiy."); return; }
      fd.append('ish_raqami', ish);
      fd.append('sana', sana);
      fd.append('ijro_varaqasi', ijroFile);
    }

    const r = await fetch(`${API_BASE}/mib/otkazildi`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    if (data.rad_etildi) alert("Sud qarori 'Rad etildi' deb qayd etildi. Bu ish MIBga o'tkazilmaydi.");
    if (data.ogohlantirish) alert(data.ogohlantirish);
    await ekranniOchish('mib');
  });
}

async function mibFaolChizish() {
  try {
    const body = document.getElementById('mib-body');
    const data = await apiGet('/mib/faol');
    window._mibFaolCache = data.royxat;
    body.innerHTML = `
      <div class="toolbar">
        <input class="tb-input" id="mib-qidiruv" placeholder="Anketa raqami" style="width:140px;">
        <button class="btn" id="mib-qidirish-btn">🔍 Topish</button>
        <button class="btn" id="mib-qidiruv-tozalash">✕ Tozalash</button>
        <span style="width:1px; height:22px; background:var(--border); margin:0 2px;"></span>
        <button class="btn" id="mib-avto-royxat">🚗 Avtomashinalar</button>
        <button class="btn" id="mib-avto-import">📥 Excel orqali yuklash</button>
        <input type="file" id="mib-avto-file" accept=".xlsx,.xls" style="display:none;">
        <button class="btn" id="mib-avto-export">📊 Xatlanmagan eksport</button>
        <button class="btn" id="mib-jarayon-excel">📊 Ro'yxatni eksport</button>
        <button class="btn-gold" id="mib-eski-ish" style="margin-left:auto;">📁 Eski MIB ishini kiritish</button>
      </div>
      <div id="mib-faol-tbody-wrap"></div>
    `;
    mibFaolJadvalniChizish(data.royxat);

    document.getElementById('mib-qidirish-btn').addEventListener('click', mibQidirish);
    document.getElementById('mib-qidiruv').addEventListener('keydown', (e) => { if (e.key === 'Enter') mibQidirish(); });
    document.getElementById('mib-qidiruv-tozalash').addEventListener('click', () => {
      document.getElementById('mib-qidiruv').value = '';
      mibFaolJadvalniChizish(window._mibFaolCache);
    });
    document.getElementById('mib-eski-ish').addEventListener('click', mibEskiIshDialogOchish);
    document.getElementById('mib-avto-royxat').addEventListener('click', () => mibAvtomashinalarDialogOchish(null));
    document.getElementById('mib-avto-import').addEventListener('click', () => document.getElementById('mib-avto-file').click());
    document.getElementById('mib-avto-file').addEventListener('change', async (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const fd = new FormData();
      fd.append('file', f);
      const r = await fetch(`${API_BASE}/mib/avtomashinalar_import`, { method: 'POST', body: fd });
      const res = await r.json();
      if (res.xato) { alert('Xato: ' + res.xato); return; }
      let msg = `${res.qoshildi} ta avtomashina muvaffaqiyatli qo'shildi.`;
      if (res.topilmadi && res.topilmadi.length) msg += `\n${res.topilmadi.length} ta qator uchun mos MIB ishi topilmadi.`;
      alert(msg);
      e.target.value = '';
    });
    document.getElementById('mib-avto-export').addEventListener('click', () => {
      window.open(`${API_BASE}/mib/avtomashinalar_xatlanmagan_excel`, '_blank');
    });
    document.getElementById('mib-jarayon-excel').addEventListener('click', () => {
      window.open(`${API_BASE}/mib/jarayondagilar_excel`, '_blank');
    });
  } catch (e) {
    const xatoJoy = document.querySelector('#mib-body, #sud-body, #tn-body') || document.getElementById('main-content');
    if (xatoJoy) xatoJoy.innerHTML = `<div class="page-sub" style="color:var(--err);">Xato yuz berdi: ${e.message}</div>`;
  }

}

async function mibQidirish() {
  const anketa = document.getElementById('mib-qidiruv').value.trim();
  if (!anketa) return;
  const data = await apiGet(`/mib/qidirish?anketa=${encodeURIComponent(anketa)}`);
  if (!data.topildi) { alert("Bu anketa MIB jarayonida topilmadi."); return; }
  mibFaolJadvalniChizish([data.row]);
}

function mibFaolJadvalniChizish(royxat) {
  const wrap = document.getElementById('mib-faol-tbody-wrap');
  wrap.innerHTML = `
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Qarzdorlik</th>
            <th>MIB ish raqami</th><th>So'nggi harakat</th><th>Bugungi-Ijro farqi</th>
            <th>💰 To'langan summa</th>
            <th>Nazorat holati</th><th>Yig'ma jild</th><th></th>
          </tr></thead>
          <tbody>
            ${royxat.map(r => `<tr>
              <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td>
              <td>${formatSum(r.qarzdorlik)}</td><td>${r.mib_ish_raqami}</td>
              <td>${r.songgi_harakat} ${r.songgi_harakat_sana ? '(' + r.songgi_harakat_sana + ')' : ''}</td>
              <td>${formatSum(r.farq)}</td>
              <td>${r.tolangan_summa > 0 ? `<a href="#" data-anketa="${r.anketa_raqami}" data-act="tolov-tafsilot" style="font-weight:600; color:var(--stamp);">${formatSum(r.tolangan_summa)}</a>` : '—'}</td>
              <td>${davoHolatPill(r.nazorat === 'toxtatish' ? 'otgan' : (r.nazorat === 'qoshimcha' ? 'tayyor' : 'yoq'), r.nazorat_matn)}</td>
              <td>${r.yigma_jild_bor ? `<a href="#" data-anketa="${r.anketa_raqami}" data-act="mib-jild-fayllar" style="font-size:11.5px;">📁 Jild fayllari</a>` : '<span style="color:var(--muted); font-size:11.5px;">—</span>'}</td>
              <td>
                ${ochiladiganMenyu('mib-amallar-' + r.anketa_raqami, 'Amallar', `
                  <button class="btn" data-anketa="${r.anketa_raqami}" data-act="mib-harakat" style="display:block; width:100%; text-align:left; margin-bottom:4px;">+ Harakat</button>
                  <button class="btn" data-anketa="${r.anketa_raqami}" data-act="mib-tarix" style="display:block; width:100%; text-align:left; margin-bottom:4px;">📋 Tarix</button>
                  <button class="btn" data-anketa="${r.anketa_raqami}" data-act="mib-avto" style="display:block; width:100%; text-align:left; margin-bottom:4px;">🚗 Mashina</button>
                  <button class="btn" data-anketa="${r.anketa_raqami}" data-act="mib-tayyor-jild" style="display:block; width:100%; text-align:left; margin-bottom:4px;">📥 Tayyor jildni olish (PDF)</button>
                  <button class="btn" data-anketa="${r.anketa_raqami}" data-act="anketa-tarixi" style="display:block; width:100%; text-align:left; margin-bottom:4px;">📜 Anketa tarixi (barcha sikllar)</button>
                  <button class="btn danger" data-anketa="${r.anketa_raqami}" data-act="mib-yakunlash" style="display:block; width:100%; text-align:left;">To'xtatish</button>
                `)}
              </td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
  royxat.forEach(r => ochiladiganMenyuIshga('mib-amallar-' + r.anketa_raqami));
  wrap.querySelectorAll('[data-act="mib-harakat"]').forEach(btn => btn.addEventListener('click', () => mibHarakatDialog(btn.dataset.anketa)));
  wrap.querySelectorAll('[data-act="mib-yakunlash"]').forEach(btn => btn.addEventListener('click', () => mibYakunlashDialog(btn.dataset.anketa)));
  wrap.querySelectorAll('[data-act="mib-tarix"]').forEach(btn => btn.addEventListener('click', () => mibTarixDialogOchish(btn.dataset.anketa)));
  wrap.querySelectorAll('[data-act="mib-tayyor-jild"]').forEach(btn => btn.addEventListener('click', () => {
    tayyorJildYuklabOlish(`${API_BASE}/mib/tayyor_jild?anketa=${encodeURIComponent(btn.dataset.anketa)}`);
  }));
  wrap.querySelectorAll('[data-act="anketa-tarixi"]').forEach(btn => btn.addEventListener('click', () => anketaTarixiDialogOchish(btn.dataset.anketa)));
  wrap.querySelectorAll('[data-act="mib-avto"]').forEach(btn => btn.addEventListener('click', () => mibAvtomashinalarDialogOchish(btn.dataset.anketa)));
  wrap.querySelectorAll('[data-act="mib-jild-fayllar"]').forEach(btn => btn.addEventListener('click', (e) => {
    e.preventDefault();
    mibJildFayllarDialogOchish(btn.dataset.anketa);
  }));
  wrap.querySelectorAll('[data-act="tolov-tafsilot"]').forEach(btn => btn.addEventListener('click', (e) => {
    e.preventDefault();
    tolovTafsilotDialogOchish(btn.dataset.anketa);
  }));
}

async function tolovTafsilotDialogOchish(anketa) {
  const data = await apiGet(`/mib/anketa_tolovlari?anketa=${encodeURIComponent(anketa)}`);
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:520px;max-height:80vh;overflow-y:auto;">
      <div style="font-size:16px;font-weight:700;margin-bottom:4px;">To'lovlar tafsiloti — ${anketa}</div>
      <div class="page-sub" style="margin:0 0 14px;">Jami to'langan: <b>${formatSum(data.jami)}</b></div>
      <table style="width:100%; font-size:12.5px;">
        <thead><tr style="text-align:left; color:var(--muted);"><th>Sana</th><th>Summa</th><th>Manba</th><th>PINFL/STIR/Hisob</th></tr></thead>
        <tbody>
          ${data.royxat.map(t => `<tr>
            <td style="padding:5px 0;">${t.sana}</td><td>${formatSum(t.summa)}</td>
            <td>${t.manba === 'kunlik_29801' ? 'Kunlik (29801)' : 'MIBdan'}</td>
            <td>${t.pinfl_yoki_stir}</td>
          </tr>`).join('')}
        </tbody>
      </table>
      <div style="display:flex; justify-content:flex-end; margin-top:16px;">
        <button class="btn" id="tt-yopish">Yopish</button>
      </div>
    </div>`);
  overlay.querySelector('#tt-yopish').addEventListener('click', () => overlay.remove());
}

function mibOverlayOchish(html) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = html;
  document.body.appendChild(overlay);
  return overlay;
}

async function mibTarixDialogOchish(anketa) {
  const data = await apiGet(`/mib/amallar_tarixi?anketa=${encodeURIComponent(anketa)}`);
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:560px;max-height:80vh;overflow-y:auto;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Harakatlar tarixi — ${anketa}</div>
      ${data.amallar.length === 0 ? '<div class="page-sub">Hali hech qanday harakat qayd qilinmagan.</div>' : `
      <table style="width:100%; font-size:12.5px;">
        <thead><tr style="text-align:left; color:var(--muted);"><th>Sana</th><th>Turi</th><th>Tavsif</th></tr></thead>
        <tbody>
          ${data.amallar.map(a => `<tr><td style="padding:6px 0;">${a.amal_sanasi}</td><td>${AMAL_TURLARI_LABEL[a.amal_turi] || a.amal_turi}</td><td>${a.tavsif || ''}</td></tr>`).join('')}
        </tbody>
      </table>`}
      <div style="display:flex; justify-content:flex-end; margin-top:16px;">
        <button class="btn" id="mt-tarix-yopish">Yopish</button>
      </div>
    </div>`);
  overlay.querySelector('#mt-tarix-yopish').addEventListener('click', () => overlay.remove());
}

const AMAL_TURLARI_LABEL = {
  oylik_ish_haqqi: "Oylik ish haqqiga qaratildi", avto_taqiq: "Avto transportga taqiq qo'yildi",
  avto_qidiruv: "Avto transport qidiruvga berildi", chetga_chiqish_taqiq: "Chetga chiqishga taqiq qo'yilgan",
  majburiy_xatlov: "Majburiy xatlov o'tkazildi", sotish_togridan: "To'g'ridan-to'g'ri sotildi",
  sotish_auksion: "Auksion yo'li bilan sotildi", kafil_ish: "Kafil bo'yicha ish qilindi",
  garov_xatlov: "Garov mulkiga xatlov o'tkazildi", garov_sotish: "Garov mulki sotildi",
  eski_ish_kiritildi: "Eski ish sifatida bazaga kiritildi", ish_haqiga_qaratish: "Oylik ish haqqiga qaratildi",
};

async function mibJildFayllarDialogOchish(anketa) {
  const data = await apiGet(`/mib/jild_fayllari?anketa=${encodeURIComponent(anketa)}`);
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:480px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:6px;">Yig'ma jild fayllari — ${anketa}</div>
      <div style="font-size:11px; color:var(--muted); margin-bottom:12px; word-break:break-all;">${data.papka}</div>
      ${data.fayllar.length === 0 ? '<div class="page-sub">Papkada fayl topilmadi.</div>' :
        data.fayllar.map(f => `<div style="padding:5px 0;">${vafotFaylKnop(f.yoli, f.nomi)}</div>`).join('')}
      <div style="display:flex; justify-content:flex-end; margin-top:16px;">
        <button class="btn" id="mj-yopish">Yopish</button>
      </div>
    </div>`);
  overlay.querySelector('#mj-yopish').addEventListener('click', () => overlay.remove());
}

function mibEskiIshDialogOchish() {
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:440px;max-height:85vh;overflow-y:auto;">
      <div style="font-size:16px;font-weight:700;margin-bottom:6px;">Eski MIB ishini kiritish</div>
      <div class="page-sub" style="margin:0 0 12px;">Bu dasturdan tashqarida avvalroq MIBga topshirilgan ish uchun.</div>
      <label style="display:block;margin-bottom:8px;">Anketa raqami<br>
        <div style="display:flex; gap:6px;">
          <input class="tb-input" id="ei-anketa" style="flex:1;">
          <button class="btn" id="ei-qidirish">🔍 Topish</button>
        </div></label>
      <div id="ei-natija" style="font-size:12.5px; color:var(--muted); margin-bottom:10px;">Hali qidirilmagan</div>
      <label style="display:block;margin-bottom:8px;">MIB ish raqami<br><input class="tb-input" id="ei-ish" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Sud ish raqami (ixtiyoriy)<br><input class="tb-input" id="ei-sud" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">MIBga o'tkazilgan sana<br><input class="tb-input" id="ei-sana" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Hozirgi qarzdorlik (ixtiyoriy, bo'sh — portfeldan olinadi)<br><input class="tb-input" id="ei-qarz" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Ijro varaqasi (PDF) — <b style="color:var(--err);">majburiy</b><br>
        <input type="file" id="ei-ijro-file" accept=".pdf" style="width:100%; margin-top:4px;"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="ei-cancel">Bekor qilish</button>
        <button class="btn-gold" id="ei-save" style="margin-left:0;">✓ Kiritish</button>
      </div>
    </div>`);
  overlay.querySelector('#ei-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#ei-qidirish').addEventListener('click', async () => {
    const anketa = overlay.querySelector('#ei-anketa').value.trim();
    if (!anketa) return;
    const data = await apiGet(`/mib/eski_ish_qidirish?anketa=${encodeURIComponent(anketa)}`);
    overlay.querySelector('#ei-natija').textContent = data.topildi
      ? `Topildi: ${data.mijoz_nomi} (${data.turi}), qarzdorlik: ${formatSum(data.jami_qarz)}`
      : "Bu anketa portfelda topilmadi.";
  });
  overlay.querySelector('#ei-save').addEventListener('click', async () => {
    const anketa = overlay.querySelector('#ei-anketa').value.trim();
    const ish = overlay.querySelector('#ei-ish').value.trim();
    const sana = overlay.querySelector('#ei-sana').value.trim();
    const ijroFile = overlay.querySelector('#ei-ijro-file').files[0];
    if (!anketa || !ish || !sana) { alert('Anketa, ish raqami va sanani kiriting.'); return; }
    if (!ijroFile) { alert("Ijro varaqasi (PDF) yuklash majburiy."); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('ish_raqami', ish);
    fd.append('sana', sana);
    fd.append('sud_ish_raqami', overlay.querySelector('#ei-sud').value.trim());
    fd.append('qarzdorlik', overlay.querySelector('#ei-qarz').value.trim());
    fd.append('ijro_varaqasi', ijroFile);
    const r = await fetch(`${API_BASE}/mib/eski_ish_kiritish`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    if (data.ogohlantirish) alert(data.ogohlantirish);
    await ekranniOchish('mib');
  });
}

async function mibAvtomashinalarDialogOchish(anketaOrNull) {
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:600px;max-height:80vh;overflow-y:auto;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Avtomashinalar ${anketaOrNull ? '— ' + anketaOrNull : '(barchasi)'}</div>
      ${anketaOrNull ? `
      <div class="card" style="margin-bottom:14px;">
        <div class="card-h">Yangi mashina qo'shish</div>
        <input class="tb-input" id="am-rusumi" placeholder="Rusumi" style="width:100%; margin-bottom:6px;">
        <input class="tb-input" id="am-davlat" placeholder="Davlat raqami" style="width:100%; margin-bottom:6px;">
        <input class="tb-input" id="am-pinfl" placeholder="Mijoz PINFL" style="width:100%; margin-bottom:6px;">
        <button class="btn-gold" id="am-qoshish" style="margin-left:0;">+ Qo'shish</button>
      </div>` : ''}
      <div id="am-royxat"></div>
      <div style="display:flex; justify-content:flex-end; margin-top:16px;">
        <button class="btn" id="am-yopish">Yopish</button>
      </div>
    </div>`);
  overlay.querySelector('#am-yopish').addEventListener('click', () => overlay.remove());

  async function royxatniYangilash() {
    const url = anketaOrNull ? `/mib/avtomashinalar?anketa=${encodeURIComponent(anketaOrNull)}` : `/mib/avtomashinalar?anketa=__barchasi__`;
    let mashinalar = [];
    if (anketaOrNull) {
      mashinalar = (await apiGet(`/mib/avtomashinalar?anketa=${encodeURIComponent(anketaOrNull)}`)).mashinalar;
    }
    const royxatDiv = overlay.querySelector('#am-royxat');
    if (!anketaOrNull) {
      royxatDiv.innerHTML = `<div class="page-sub">Bitta mijozning mashinalarini ko'rish uchun jadvaldagi "🚗 Mashina" tugmasidan foydalaning. Bu oyna umumiy Excel import/eksport uchun.</div>`;
      return;
    }
    royxatDiv.innerHTML = mashinalar.length === 0 ? '<div class="page-sub">Hali mashina qo\'shilmagan.</div>' :
      mashinalar.map(m => `
        <div class="card" style="margin-bottom:8px;">
          <div style="font-weight:600;">${m.mashina_rusumi} — ${m.davlat_raqami}</div>
          <div style="font-size:11.5px; color:var(--muted); margin-bottom:6px;">Holat: ${m.holati} ${m.holat_sanasi ? '(' + m.holat_sanasi + ')' : ''}</div>
          <div class="btn-row">
            <select class="tb-select" id="am-holati-${m.id}">
              <option value="xatlanmagan" ${m.holati === 'xatlanmagan' ? 'selected' : ''}>Xatlanmagan</option>
              <option value="taqiq" ${m.holati === 'taqiq' ? 'selected' : ''}>Taqiq qo'yildi</option>
              <option value="qidiruv" ${m.holati === 'qidiruv' ? 'selected' : ''}>Qidiruvga berildi</option>
              <option value="xatlangan" ${m.holati === 'xatlangan' ? 'selected' : ''}>Xatlangan</option>
            </select>
            <input class="tb-input" id="am-modda-${m.id}" placeholder="Modda" value="${m.modda || ''}" style="width:100px;">
            <input type="file" id="am-hujjat-${m.id}" style="width:140px;">
            <button class="btn" data-id="${m.id}" data-act="am-saqlash">Saqlash</button>
          </div>
          ${m.asoslovchi_hujjat_fayl ? vafotFaylKnop(m.asoslovchi_hujjat_fayl, 'Hujjatni ochish') : ''}
        </div>
      `).join('');
    royxatDiv.querySelectorAll('[data-act="am-saqlash"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        const fd = new FormData();
        fd.append('id', id);
        fd.append('holati', overlay.querySelector(`#am-holati-${id}`).value);
        fd.append('modda', overlay.querySelector(`#am-modda-${id}`).value);
        const fileInp = overlay.querySelector(`#am-hujjat-${id}`);
        if (fileInp.files[0]) fd.append('hujjat', fileInp.files[0]);
        await fetch(`${API_BASE}/mib/avtomashina_holati`, { method: 'POST', body: fd });
        await royxatniYangilash();
      });
    });
  }
  await royxatniYangilash();

  if (anketaOrNull) {
    overlay.querySelector('#am-qoshish').addEventListener('click', async () => {
      const rusumi = overlay.querySelector('#am-rusumi').value.trim();
      const davlat = overlay.querySelector('#am-davlat').value.trim();
      const pinfl = overlay.querySelector('#am-pinfl').value.trim();
      if (!rusumi || !davlat) { alert('Rusumi va davlat raqamini kiriting.'); return; }
      await fetch(`${API_BASE}/mib/avtomashina_qoshish`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anketa_raqami: anketaOrNull, rusumi, davlat_raqami: davlat, pinfl }),
      });
      overlay.querySelector('#am-rusumi').value = '';
      overlay.querySelector('#am-davlat').value = '';
      overlay.querySelector('#am-pinfl').value = '';
      await royxatniYangilash();
    });
  }
}

async function mibHarakatDialog(anketa) {
  const turlarData = await apiGet('/mib/harakat_turlari');
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:420px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Yangi harakat — ${anketa}</div>
      <label style="display:block;margin-bottom:8px;">Harakat turi<br>
        <select class="tb-select" id="mh-turi" style="width:100%;">
          ${turlarData.turlar.length === 0
            ? '<option value="">— Avval Sozlamalarda harakat turi qo\'shing —</option>'
            : turlarData.turlar.map(t => `<option value="${t.nomi}">${t.nomi}</option>`).join('')}
        </select></label>
      <label style="display:block;margin-bottom:8px;">Sana (kun.oy.yil)<br><input class="tb-input" id="mh-sana" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Tavsif<br><textarea class="tb-input" id="mh-tavsif" style="width:100%;" rows="2"></textarea></label>
      <label style="display:block;margin-bottom:8px;">Undirilgan summa (ixtiyoriy)<br><input class="tb-input" id="mh-summa" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Tasdiqlovchi hujjat (PDF) — majburiy<br><input type="file" id="mh-hujjat" accept=".pdf" style="width:100%; margin-top:4px;"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="mh-cancel">Bekor qilish</button>
        <button class="btn-gold" id="mh-save" style="margin-left:0;">✓ Saqlash</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  document.getElementById('mh-cancel').addEventListener('click', () => overlay.remove());
  document.getElementById('mh-save').addEventListener('click', async () => {
    const sana = document.getElementById('mh-sana').value.trim();
    if (!sana) { alert('Sanani kiriting.'); return; }
    const turi = document.getElementById('mh-turi').value;
    if (!turi) { alert("Harakat turini tanlang (avval Sozlamalarda qo'shing)."); return; }
    const hujjat = document.getElementById('mh-hujjat').files[0];
    if (!hujjat) { alert("Tasdiqlovchi hujjat (PDF) yuklash majburiy."); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('amal_turi', turi);
    fd.append('amal_sanasi', sana);
    fd.append('tavsif', document.getElementById('mh-tavsif').value);
    fd.append('undirilgan_summa', document.getElementById('mh-summa').value || '');
    fd.append('tasdiqlovchi_hujjat', hujjat);
    const res = await fetch(`${API_BASE}/mib/amal_qoshish`, { method: 'POST', body: fd });
    const d = await res.json();
    if (d.xato) { alert('Xato: ' + d.xato); return; }
    overlay.remove();
    await ekranniOchish('mib');
  });
}

function mibYakunlashDialog(anketa) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:400px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">To'xtatish / Yakunlash — ${anketa}</div>
      <label style="display:block;margin-bottom:8px;">Sabab/izoh<br><textarea class="tb-input" id="my-sabab" style="width:100%;" rows="2"></textarea></label>
      <label style="display:block;margin-bottom:8px;">Sana (kun.oy.yil)<br><input class="tb-input" id="my-sana" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Yakunlash asosi hujjati (PDF) — <b style="color:var(--err);">MAJBURIY</b><br>
        <input type="file" id="my-file" accept=".pdf"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="my-cancel">Bekor qilish</button>
        <button class="btn-gold" id="my-save" style="margin-left:0;">✓ Yakunlash</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  document.getElementById('my-cancel').addEventListener('click', () => overlay.remove());
  document.getElementById('my-save').addEventListener('click', async () => {
    const sabab = document.getElementById('my-sabab').value.trim();
    const sana = document.getElementById('my-sana').value.trim();
    const f = document.getElementById('my-file').files[0];
    if (!sabab) { alert('Sabab/izohni kiriting.'); return; }
    if (!f) { alert("Yakunlash asosi hujjatini (PDF) yuklang — bu majburiy."); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('sabab', sabab);
    fd.append('sana', sana);
    fd.append('asos_hujjat', f);
    const r = await fetch(`${API_BASE}/mib/yakunlash`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    await ekranniOchish('mib');
  });
}

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

async function mibYakunlanganChizish() {
  try {
    const body = document.getElementById('mib-body');
    const data = await apiGet('/mib/yakunlangan');
    body.innerHTML = `
      <div class="toolbar">
        <button class="btn-gold" id="mib-yakunlangan-excel" style="margin-left:0;">📊 Excelga eksport</button>
      </div>
      <div class="table-wrap">
        <div class="table-scroll">
          <table>
            <thead><tr>
              <th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>MIB ish raqami</th>
              <th>Yakunlangan sana</th><th>Sabab</th><th></th>
            </tr></thead>
            <tbody>
              ${data.royxat.map(r => `<tr>
                <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td>
                <td>${r.mib_ish_raqami}</td><td>${r.yakunlangan_sana}</td><td>${r.sabab}</td>
                <td>
                  <button class="btn" data-anketa="${r.anketa_raqami}" data-act="mib-reopen">↩ Qayta ochish</button>
                  <button class="btn" data-anketa="${r.anketa_raqami}" data-act="anketa-tarixi-yakun">📜 Tarix</button>
                  <button class="btn danger" data-anketa="${r.anketa_raqami}" data-act="mib-nollash">🗑 Nollashtirish</button>
                </td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
    document.getElementById('mib-yakunlangan-excel').addEventListener('click', () => {
      tayyorJildYuklabOlish(`${API_BASE}/mib/yakunlangan_excel`);
    });
    body.querySelectorAll('[data-act="mib-reopen"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        await fetch(`${API_BASE}/mib/qayta_ochish`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ anketa_raqami: btn.dataset.anketa }),
        });
        await ekranniOchish('mib');
      });
    });
    body.querySelectorAll('[data-act="anketa-tarixi-yakun"]').forEach(btn => {
      btn.addEventListener('click', () => anketaTarixiDialogOchish(btn.dataset.anketa));
    });
    body.querySelectorAll('[data-act="mib-nollash"]').forEach(btn => {
      btn.addEventListener('click', () => mibNollashDialogOchish(btn.dataset.anketa));
    });
  } catch (e) {
    const xatoJoy = document.querySelector('#mib-body, #sud-body, #tn-body') || document.getElementById('main-content');
    if (xatoJoy) xatoJoy.innerHTML = `<div class="page-sub" style="color:var(--err);">Xato yuz berdi: ${e.message}</div>`;
  }

}

// ---------------- CHORA KO'RISH ----------------
let choraBelgilangan = new Set();
let choraRoyxatCache = [];
let choraQidiruvNatija = null;

async function choraKorishniYuklash(main) {
  const data = await apiGet('/chora/royxat');
  choraRoyxatCache = data.royxat;
  choraBelgilangan.clear();
  choraKorsatilganSoni = 200;
  choraQidiruvNatija = null;

  main.innerHTML = `
    <div class="page-title">Chora ko'rish</div>
    <div class="page-sub">Portfel avtomatik tahlil qilinib, muddati o'tgan (DPD) kuniga qarab har bir mijoz uchun chora ko'rsatiladi.</div>

    <div class="stat-row">
      <div class="stat-card"><div class="stat-num">${data.soni['xat_yuborish'] || 0}</div>
        <div class="stat-label">Ogohlantirish/Talabnoma kerak</div></div>
      <div class="stat-card"><div class="stat-num">${data.soni['xat_yuborish_keyingi_bosqich'] || 0}</div>
        <div class="stat-label">Xat kerak (Davo arizaga o'tish uchun)</div></div>
      <div class="stat-card"><div class="stat-num warn">${data.soni['davo_ariza_tayyorlash'] || 0}</div>
        <div class="stat-label">Davo ariza kerak</div></div>
      <div class="stat-card"><div class="stat-num warn">${data.soni['mib_harakat_boshlash'] || 0}</div>
        <div class="stat-label">MIB harakat kerak</div></div>
    </div>

    <div class="primary-bar">
      <span style="color:var(--ice); font-size:12.5px;">Belgilangan mijozlar uchun tavsiya etilgan choraga qarab (xat yoki Davo ariza) amal bajariladi.</span>
      <span class="badge-count" id="chora-count" style="margin-left:auto;">Belgilangan: 0 ta</span>
      <button class="btn-gold" id="chora-bajar">▶ Amal bajarish (tanlangan)</button>
    </div>

    <div class="toolbar">
      <input class="tb-input" id="chora-qidiruv" placeholder="Anketa raqami" style="width:130px;">
      <button class="btn" id="chora-qidirish-btn">🔍 Topish</button>
      <button class="btn" id="chora-qidiruv-tozalash">✕</button>
      <button class="btn" id="chora-select-all">☑ Hammasi</button>
      <button class="btn" id="chora-select-none">☐ Bekor qilish</button>
      <select class="tb-select" id="chora-paket" style="width:70px;">
        <option>10</option><option selected>30</option><option>50</option><option>100</option><option>Barchasi</option>
      </select>
      <button class="btn" id="chora-first-paket">① Birinchi paket</button>
      <select class="tb-select" id="chora-filter">
        <option value="">Barcha choralar</option>
        ${Object.entries(data.chora_nomlari).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}
      </select>
      <select class="tb-select" id="chora-turi-filter">
        <option value="">Barchasi (Jismoniy/Yuridik)</option>
        <option value="jismoniy">Jismoniy</option>
        <option value="yuridik">Yuridik</option>
        <option value="yatt">YaTT</option>
      </select>
      <button class="btn" id="chora-excel">📊 Excel eksport</button>
      <button class="btn" id="chora-sud-excel">⚖ Sudga topshirilganlar</button>
    </div>

    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th></th><th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>DPD</th>
            <th>Qarzdorlik</th><th>Chora</th><th>Tafsilot</th>
          </tr></thead>
          <tbody id="chora-tbody"></tbody>
        </table>
      </div>
    </div>
    <div style="text-align:center; padding: 14px 0;" id="chora-more-wrap"></div>
  `;

  document.getElementById('chora-qidiruv-tozalash').addEventListener('click', () => {
    choraQidiruvNatija = null;
    document.getElementById('chora-qidiruv').value = '';
    choraJadvalniChizish();
  });
  document.getElementById('chora-select-all').addEventListener('click', () => {
    choraJadvalFiltrlangan().forEach(r => choraBelgilangan.add(r.anketa_raqami));
    choraJadvalniChizish();
  });
  document.getElementById('chora-select-none').addEventListener('click', () => {
    choraBelgilangan.clear();
    choraJadvalniChizish();
  });
  document.getElementById('chora-filter').addEventListener('change', () => { choraKorsatilganSoni = 200; choraJadvalniChizish(); });
  document.getElementById('chora-turi-filter').addEventListener('change', () => { choraKorsatilganSoni = 200; choraJadvalniChizish(); });
  document.getElementById('chora-tbody').addEventListener('click', (e) => {
    const el = e.target.closest('.checkbox');
    if (!el) return;
    const anketa = el.dataset.anketa;
    if (choraBelgilangan.has(anketa)) { choraBelgilangan.delete(anketa); el.classList.remove('checked'); }
    else { choraBelgilangan.add(anketa); el.classList.add('checked'); }
    document.getElementById('chora-count').textContent = `Belgilangan: ${choraBelgilangan.size} ta`;
  });
  document.getElementById('chora-excel').addEventListener('click', () => {
    window.open(`${API_BASE}/chora/excel_eksport`, '_blank');
  });
  document.getElementById('chora-sud-excel').addEventListener('click', () => {
    window.open(`${API_BASE}/davo-ariza/sudga_topshirilganlar_excel`, '_blank');
  });
  document.getElementById('chora-first-paket').addEventListener('click', () => {
    const paket = document.getElementById('chora-paket').value;
    const royxat = choraJadvalFiltrlangan();
    const n = paket === 'Barchasi' ? royxat.length : parseInt(paket, 10);
    choraBelgilangan.clear();
    royxat.slice(0, n).forEach(r => choraBelgilangan.add(r.anketa_raqami));
    choraKorsatilganSoni = Math.max(choraKorsatilganSoni, n);
    choraJadvalniChizish();
  });
  document.getElementById('chora-qidirish-btn').addEventListener('click', async () => {
    const anketa = document.getElementById('chora-qidiruv').value.trim();
    if (!anketa) return;
    const res = await apiGet(`/chora/qidirish?anketa=${encodeURIComponent(anketa)}`);
    if (!res.topildi) { alert("Bu anketa Chora ko'rish ro'yxatida topilmadi."); return; }
    choraQidiruvNatija = [res.row];
    choraKorsatilganSoni = 200;
    choraJadvalniChizish();
  });
  document.getElementById('chora-bajar').addEventListener('click', async () => {
    if (choraBelgilangan.size === 0) { alert('Kamida bitta mijozni belgilang.'); return; }
    const r = await fetch(`${API_BASE}/chora/amal_bajarish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anketalar: Array.from(choraBelgilangan) }),
    });
    const result = await r.json();
    if (result.xato) { alert('Xato: ' + result.xato); return; }
    let msg = result.turi === 'xat' ? `${result.yaratildi} ta xat tayyorlandi.` : `${result.yaratildi} ta Davo ariza tayyorlandi.`;
    if (result.otkazib_yuborildi) msg += `\n${result.otkazib_yuborildi} ta o'tkazib yuborildi.`;
    alert(msg);
    await ekranniOchish('chora');
  });

  choraJadvalniChizish();
}

let choraKorsatilganSoni = 200;

function choraJadvalFiltrlangan() {
  if (choraQidiruvNatija) return choraQidiruvNatija;
  const filtr = document.getElementById('chora-filter').value;
  const turiFiltr = document.getElementById('chora-turi-filter').value;
  return choraRoyxatCache.filter(r => {
    if (filtr && r.chora !== filtr) return false;
    if (turiFiltr && r.turi !== turiFiltr) return false;
    return true;
  });
}

function choraJadvalniChizish() {
  const toliqRoyxat = choraJadvalFiltrlangan();
  const royxat = toliqRoyxat.slice(0, choraKorsatilganSoni);
  const tbody = document.getElementById('chora-tbody');
  tbody.innerHTML = royxat.map(r => {
    const checked = choraBelgilangan.has(r.anketa_raqami);
    return `<tr>
      <td><span class="checkbox ${checked ? 'checked' : ''}" data-anketa="${r.anketa_raqami}"></span></td>
      <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td><td>${r.dpd}</td>
      <td>${formatSum(r.qarzdorlik)}</td><td>${r.chora_nomi}</td><td>${r.tafsilot}</td>
    </tr>`;
  }).join('');
  document.getElementById('chora-count').textContent = `Belgilangan: ${choraBelgilangan.size} ta`;

  const qolgan = toliqRoyxat.length - choraKorsatilganSoni;
  const moreWrap = document.getElementById('chora-more-wrap');
  if (moreWrap) {
    if (qolgan > 0) {
      moreWrap.innerHTML = `<button class="btn ghost" id="chora-more-btn">⬇ Yana ${Math.min(qolgan, 200)} tasini ko'rsatish (jami ${qolgan} ta qoldi)</button>`;
      document.getElementById('chora-more-btn').addEventListener('click', () => { choraKorsatilganSoni += 200; choraJadvalniChizish(); });
    } else {
      moreWrap.innerHTML = '';
    }
  }
}

// ---------------- 95413 ----------------
async function nazorat95413niYuklash(main) {
  const data = await apiGet('/nazorat95413/royxat');

  main.innerHTML = `
    <div class="page-title">95413 nazorati (balansdan chiqarilgan kreditlar)</div>
    <div class="page-sub">"Koldik 95413" balansiga ega barcha kreditlar, DPD kunidan qat'i nazar, to'liq bosqichma-bosqich nazorat ostida.</div>

    <div class="stat-row">
      <div class="stat-card"><div class="stat-num">${formatSum(data.jami)}</div>
        <div class="stat-label">Jami kredit (${formatSum(data.jami_balans)} so'm)</div></div>
      ${Object.entries(data.bosqich_nomlari).map(([k, v]) => `
        <div class="stat-card"><div class="stat-num" style="font-size:20px;">${data.soni[k] || 0}</div>
          <div class="stat-label">${v}</div></div>`).join('')}
    </div>

    <div class="primary-bar">
      <span style="color:var(--ice); font-size:12.5px;">Belgilangan mijoz uchun joriy bosqichga mos amal shu yerning o'zida bajariladi.</span>
      <span class="badge-count" id="n95-count" style="margin-left:auto;">Belgilangan: 0 ta</span>
      <button class="btn-gold" id="n95-bajar">▶ Amal bajarish (tanlangan)</button>
    </div>

    <div class="toolbar">
      <button class="btn" id="n95-select-all">☑ Hammasini belgilash</button>
      <button class="btn" id="n95-select-none">☐ Belgilarni bekor qilish</button>
      <select class="tb-select" id="n95-filter">
        <option value="">Barcha bosqichlar</option>
        ${Object.entries(data.bosqich_nomlari).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}
      </select>
      <select class="tb-select" id="n95-turi-filter">
        <option value="">Barchasi</option>
        <option value="jismoniy">Jismoniy</option>
        <option value="yuridik">Yuridik</option>
        <option value="yatt">YaTT</option>
      </select>
      <button class="btn" id="n95-excel">📊 Excel eksport</button>
      <button class="btn-gold" id="n95-eski-ish" style="margin-left:0;">📁 Eski ish kiritish</button>
    </div>

    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr><th></th><th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Balans 95413</th><th>Bosqich</th><th>Tafsilot</th><th>Yig'ma jild</th></tr></thead>
          <tbody id="n95-tbody"></tbody>
        </table>
      </div>
    </div>
    <div style="text-align:center; padding: 14px 0;" id="n95-more-wrap"></div>
  `;

  window._n95Cache = data.royxat;
  window._n95KorsatilganSoni = 200;
  window._n95Belgilangan = new Set();
  document.getElementById('n95-filter').addEventListener('change', () => { window._n95KorsatilganSoni = 200; n95413JadvalniChizish(); });
  document.getElementById('n95-turi-filter').addEventListener('change', () => { window._n95KorsatilganSoni = 200; n95413JadvalniChizish(); });
  document.getElementById('n95-select-all').addEventListener('click', () => {
    let royxat = window._n95Cache;
    const bosqichFiltr = document.getElementById('n95-filter').value;
    const turiFiltr = document.getElementById('n95-turi-filter').value;
    if (bosqichFiltr) royxat = royxat.filter(r => r.bosqich === bosqichFiltr);
    if (turiFiltr) royxat = royxat.filter(r => r.turi === turiFiltr);
    royxat.forEach(r => window._n95Belgilangan.add(r.anketa_raqami));
    n95413JadvalniChizish();
  });
  document.getElementById('n95-select-none').addEventListener('click', () => { window._n95Belgilangan.clear(); n95413JadvalniChizish(); });
  document.getElementById('n95-eski-ish').addEventListener('click', n95413EskiIshDialogOchish);
  document.getElementById('n95-bajar').addEventListener('click', n95413AmalBajarish);
  document.getElementById('n95-excel').addEventListener('click', () => {
    window.open(`${API_BASE}/nazorat95413/excel_eksport`, '_blank');
  });
  n95413JadvalniChizish();
}

function f95413JildDialogOchish(anketa) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `<div style="background:#fff;border-radius:12px;padding:20px 24px;width:500px;max-height:85vh;overflow-y:auto;" id="f95-modal-content"><div class="loading">Yuklanmoqda...</div></div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  f95413JildModalniChizish(anketa, overlay);
}

async function f95413JildModalniChizish(anketa, overlay) {
  const content = overlay.querySelector('#f95-modal-content');
  const data = await apiGet(`/95413/yigma_jild_holati?anketa=${encodeURIComponent(anketa)}`);
  content.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
      <div style="font-size:16px; font-weight:700;">📁 95413 Yig'ma jildi — ${anketa}</div>
      <button class="btn" id="f95-yopish">✕</button>
    </div>
    <div class="btn-row" style="margin-bottom:12px;">
      <button class="btn-gold" id="f95-titul-yarat" style="margin-left:0;">
        ${data.titul_bor ? '📁 Titulni qayta yaratish' : '⚙ Titulni avtomatik yaratish'}
      </button>
      ${data.titul_bor ? `<a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(data.titul_fayl)}" target="_blank" class="btn">👁 Titulni ko'rish</a>` : ''}
    </div>
    ${data.hujjatlar.length > 0 ? `
      <table style="width:100%; font-size:12.5px; margin-bottom:10px;">
        ${data.hujjatlar.map(h => `<tr>
          <td style="padding:5px 0;">${h.hujjat_nomi}</td>
          <td><a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(h.fayl_yoli)}" target="_blank">👁 Ko'rish</a></td>
          <td><button class="btn danger" data-hujjat-id="${h.id}" style="padding:2px 8px; font-size:11px;">🗑</button></td>
        </tr>`).join('')}
      </table>
    ` : '<div class="page-sub">Hali hujjat yuklanmagan.</div>'}
    <div class="card" style="margin-top:10px; padding:10px 14px;">
      <div class="card-h" style="font-size:12.5px;">➕ Hujjat qo'shish (nomini o'zingiz yozing)</div>
      <div class="btn-row">
        <input class="tb-input" id="f95-hujjat-nomi" placeholder="Hujjat nomi (masalan: Ariza, Guvohnoma)" style="width:220px;">
        <input type="file" id="f95-hujjat-file" style="width:200px;">
        <button class="btn-gold" id="f95-hujjat-qoshish" style="margin-left:0;">📤 Qo'shish</button>
      </div>
    </div>
  `;
  content.querySelector('#f95-yopish').addEventListener('click', () => overlay.remove());
  content.querySelector('#f95-titul-yarat').addEventListener('click', async () => {
    const res = await fetch(`${API_BASE}/95413/titul_yaratish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ anketa_raqami: anketa }),
    });
    const d = await res.json();
    if (d.xato) { alert('Xato: ' + d.xato); return; }
    await f95413JildModalniChizish(anketa, overlay);
  });
  content.querySelector('#f95-hujjat-qoshish').addEventListener('click', async () => {
    const nomi = content.querySelector('#f95-hujjat-nomi').value.trim();
    const f = content.querySelector('#f95-hujjat-file').files[0];
    if (!nomi || !f) { alert("Hujjat nomi va faylni tanlang."); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('hujjat_nomi', nomi);
    fd.append('file', f);
    const res = await fetch(`${API_BASE}/95413/hujjat_yuklash`, { method: 'POST', body: fd });
    const d = await res.json();
    if (d.xato) { alert('Xato: ' + d.xato); return; }
    await f95413JildModalniChizish(anketa, overlay);
  });
  content.querySelectorAll('[data-hujjat-id]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm("Bu hujjatni o'chirasizmi?")) return;
      await fetch(`${API_BASE}/95413/hujjat/${btn.dataset.hujjatId}`, { method: 'DELETE' });
      await f95413JildModalniChizish(anketa, overlay);
    });
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
      <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td>
      <td>${formatSum(r.balans_95413)}</td><td>${r.bosqich_nomi}</td><td>${r.tafsilot}</td>
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
    if (!confirm(`${r.mijoz_nomi} uchun xat tayyorlansinmi ('Tayyor' holatida saqlanadi)?`)) return;
    const resp = await fetch(`${API_BASE}/talabnoma/xat_yaratish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ anketalar: [anketa] }),
    });
    const data = await resp.json();
    alert(data.yaratildi ? "Xat tayyorlandi ('Tayyor' holatida)." : `Xato: ${data.xatolar.join(', ')}`);
    await ekranniOchish('95413');
  } else if (r.bosqich === 'xat_yuborish_kerak') {
    if (!confirm(`${r.mijoz_nomi} xati 'Yuborildi' deb belgilansinmi?`)) return;
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
    if (!confirm(`${r.mijoz_nomi} uchun Davo ariza tayyorlansinmi?`)) return;
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
async function tahlilniYuklash(main) {
  const [t, tarixData] = await Promise.all([apiGet('/tahlil/umumiy'), apiGet('/tahlil/tarix')]);
  const tarix = tarixData.tarix;

  main.innerHTML = `
    <div class="page-title">Tahlil</div>
    <div class="page-sub">Butun portfel bo'yicha umumiy holat: jismoniy/yuridik taqsimoti, tarmoqlar kesimida va Stage 1/2/3 bo'yicha tahlil.</div>
    <div class="toolbar">
      <button class="btn" id="th-refresh">🔄 Yangilash</button>
      <span style="font-size:12.5px; color:var(--muted);">Format:</span>
      <select class="tb-select" id="th-format">
        <option value="word">Word (.docx)</option>
        <option value="pdf">PDF (.pdf)</option>
      </select>
      <button class="btn-gold" id="th-export" style="margin-left:0;">📄 Hisobotni yuklab olish</button>
    </div>

    <div class="stat-row">
      <div class="stat-card"><div class="stat-num">${formatSum(t.jami_soni)}</div><div class="stat-label">Jami portfeldagi mijozlar</div></div>
      <div class="stat-card"><div class="stat-num">${(t.jami_ead / 1e9).toFixed(1)} mlrd</div><div class="stat-label">Jami EAD qoldiq</div></div>
      <div class="stat-card"><div class="stat-num">${formatSum(t.jismoniy.soni)}</div><div class="stat-label">Jismoniy shaxslar (${(t.jismoniy.ead / 1e9).toFixed(1)} mlrd)</div></div>
      <div class="stat-card"><div class="stat-num">${formatSum(t.yuridik.soni)}</div><div class="stat-label">Yuridik shaxslar (${(t.yuridik.ead / 1e9).toFixed(1)} mlrd)</div></div>
    </div>

    <div class="card-row">
      <div class="card" style="flex:1;">
        <div class="card-h">Jismoniy / Yuridik taqsimoti (EAD bo'yicha)</div>
        <div style="position:relative; height:230px;"><canvas id="th-pie-chart"></canvas></div>
      </div>
      <div class="card" style="flex:1;">
        <div class="card-h">Stage 1 / 2 / 3 taqqoslash</div>
        <div style="position:relative; height:230px;"><canvas id="th-stage-chart"></canvas></div>
      </div>
    </div>

    <div class="card" style="margin-bottom:16px;">
      <div class="card-h">📈 Vaqt bo'yicha tendensiya — Stage 3 (yuqori xavfli) kreditlar soni</div>
      ${tarix.length < 2
        ? `<div class="page-sub" style="margin:0;">Hozircha faqat ${tarix.length} ta o'lchov mavjud. Portfelni har safar yangilaganingizda (Portfel bo'limi orqali) yangi nuqta avtomatik qo'shiladi — bir necha yangilanishdan keyin bu yerda haqiqiy tendensiya grafigi paydo bo'ladi.</div>`
        : `<div style="position:relative; height:220px;"><canvas id="th-trend-chart"></canvas></div>`
      }
    </div>

    <div class="card-h" style="margin-bottom:10px;">Tarmoq (soha) kesimida — EAD summasi bo'yicha
      <span style="font-weight:400; color:var(--muted); font-size:11px;">— qatorga bosib, mijozlar ro'yxatini ko'ring</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Tarmoq</th><th>Soni</th><th>EAD summasi</th></tr></thead>
        <tbody id="th-tarmoq-tbody">
          ${t.tarmoq.map(r => `<tr class="th-tarmoq-row" data-tarmoq="${r.tarmoq}" style="cursor:pointer;">
            <td>${r.tarmoq}</td><td>${formatSum(r.soni)}</td><td>${(r.ead / 1e9).toFixed(2)} mlrd</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  `;
  document.getElementById('th-refresh').addEventListener('click', () => tahlilniYuklash(main));
  document.getElementById('th-export').addEventListener('click', () => {
    const fmt = document.getElementById('th-format').value;
    window.open(`${API_BASE}/tahlil/hisobot_yuklab_olish?format=${fmt}`, '_blank');
  });

  document.querySelectorAll('.th-tarmoq-row').forEach(row => {
    row.addEventListener('mouseenter', () => row.style.background = '#EEF1FC');
    row.addEventListener('mouseleave', () => row.style.background = '');
    row.addEventListener('click', () => thTarmoqMijozlariDialogOchish(row.dataset.tarmoq));
  });

  // ---- Grafiklar (Chart.js) ----
  new Chart(document.getElementById('th-pie-chart'), {
    type: 'doughnut',
    data: {
      labels: ['Jismoniy shaxslar', 'Yuridik shaxslar'],
      datasets: [{ data: [t.jismoniy.ead / 1e9, t.yuridik.ead / 1e9], backgroundColor: ['#1E2761', '#C9A227'], borderWidth: 0 }],
    },
    options: { plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } }, maintainAspectRatio: false },
  });

  new Chart(document.getElementById('th-stage-chart'), {
    type: 'bar',
    data: {
      labels: t.stage.map(s => `Stage ${s.stage}`),
      datasets: [{ data: t.stage.map(s => s.soni), backgroundColor: ['#1E2761', '#C9A227', '#C0392B'], borderRadius: 6 }],
    },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } }, maintainAspectRatio: false },
  });

  if (tarix.length >= 2) {
    new Chart(document.getElementById('th-trend-chart'), {
      type: 'line',
      data: {
        labels: tarix.map(r => r.sana.slice(5)),
        datasets: [{ label: 'Stage 3 soni', data: tarix.map(r => r.stage3_soni),
          borderColor: '#C0392B', backgroundColor: 'rgba(192,57,43,0.08)', fill: true, tension: 0.3 }],
      },
      options: { plugins: { legend: { display: false } }, maintainAspectRatio: false },
    });
  }
}

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
            <td style="padding:5px 0;">${m.anketa_raqami}</td><td>${m.mijoz_nomi}</td><td>${m.mijoz_turi}</td>
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

async function vafotEtganlarniYuklash(main) {
  const data = await apiGet('/vafot/royxat');
  main.innerHTML = `
    <div class="page-title">Vafot etgan mijozlar</div>
    <div class="page-sub">Vafot etgan mijozlarga nisbatan hech qanday undirish chorasi (xat, Davo ariza, MIB) ko'rilmaydi — ular avtomatik boshqa bo'limlar ro'yxatidan chiqarib tashlanadi.</div>

    <div class="toolbar">
      <button class="btn-gold" id="vafot-add" style="margin-left:0;">+ Yangi vafot etgan mijoz</button>
      <button class="btn" id="vafot-excel">📊 Excel'ga eksport qilish</button>
    </div>

    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th>Anketa №</th><th>Mijoz</th><th>Vafot sanasi</th><th>Polis holati</th>
            <th>Sug'urta kompaniya</th><th>Xabarnoma holati</th><th>Hujjatlar</th><th></th>
          </tr></thead>
          <tbody>
            ${data.royxat.map(r => `<tr>
              <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.vafot_sanasi}</td>
              <td>${davoHolatPill(r.polis_holati === 'amalda' ? 'olib_kelindi' : 'tayyor', r.polis_holati)}</td>
              <td>${r.sugurta_kompaniya || '—'}</td><td>${r.xabarnoma_holati || 'kerak'}</td>
              <td style="display:flex; flex-direction:column; gap:3px;">
                ${vafotFaylKnop(r.olimlik_guvohnomasi_fayl, "O'limlik")}
                ${vafotFaylKnop(r.pasport_fayl, 'Pasport')}
                ${vafotFaylKnop(r.sugurta_polis_fayl, 'Polis')}
              </td>
              <td>
                <button class="btn" data-id="${r.id}" data-act="vafot-fayl">📎 Hujjat</button>
                <button class="btn" data-id="${r.id}" data-polis="${r.polis_holati}" data-act="vafot-sugurta">💼 Sug'urta</button>
                ${r.polis_holati === 'amalda' && r.sugurta_kompaniya ? `<button class="btn" data-id="${r.id}" data-act="vafot-xabarnoma">✉ Xabarnoma</button>` : ''}
                ${r.xabarnoma_holati === 'kerak' && r.sugurta_kompaniya ? `<button class="btn" data-id="${r.id}" data-mijoz="${r.mijoz_nomi}" data-act="vafot-xab-yuborildi">✓ Yuborildi</button>` : ''}
                ${r.xabarnoma_holati === 'yuborildi' ? `<button class="btn" data-id="${r.id}" data-mijoz="${r.mijoz_nomi}" data-act="vafot-javob-keldi">✓ Javob keldi</button>` : ''}
              </td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
  main.querySelectorAll('[data-act="vafot-fayl"]').forEach(btn => btn.addEventListener('click', () => vafotFaylDialogOchish(btn.dataset.id)));
  main.querySelectorAll('[data-act="vafot-sugurta"]').forEach(btn => btn.addEventListener('click', () => vafotSugurtaDialogOchish(btn.dataset.id, btn.dataset.polis)));
  main.querySelectorAll('[data-act="vafot-xabarnoma"]').forEach(btn => btn.addEventListener('click', () => vafotXabarnomaTayyorlash(btn.dataset.id)));
  main.querySelectorAll('[data-act="vafot-xab-yuborildi"]').forEach(btn => btn.addEventListener('click', () => vafotXabYuborildiDialog(btn.dataset.id, btn.dataset.mijoz)));
  main.querySelectorAll('[data-act="vafot-javob-keldi"]').forEach(btn => btn.addEventListener('click', () => vafotJavobKeldiDialog(btn.dataset.id, btn.dataset.mijoz)));
  document.getElementById('vafot-excel').addEventListener('click', () => {
    window.open(`${API_BASE}/vafot/excel`, '_blank');
  });
  document.getElementById('vafot-add').addEventListener('click', () => {
    const overlay = document.createElement('div');
    overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
    overlay.innerHTML = `
      <div style="background:#fff;border-radius:12px;padding:20px 24px;width:380px;">
        <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Yangi vafot etgan mijoz</div>
        <label style="display:block;margin-bottom:8px;">Anketa raqami<br><input class="tb-input" id="va-anketa" style="width:100%;"></label>
        <label style="display:block;margin-bottom:8px;">Vafot sanasi (kun.oy.yil)<br><input class="tb-input" id="va-sana" style="width:100%;"></label>
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
          <button class="btn" id="va-cancel">Bekor qilish</button>
          <button class="btn-gold" id="va-save" style="margin-left:0;">✓ Saqlash</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    document.getElementById('va-cancel').addEventListener('click', () => overlay.remove());
    document.getElementById('va-save').addEventListener('click', async () => {
      const anketa = document.getElementById('va-anketa').value.trim();
      const sana = document.getElementById('va-sana').value.trim();
      if (!anketa || !sana) { alert('Anketa raqami va sanani kiriting.'); return; }
      const r = await fetch(`${API_BASE}/vafot/qoshish`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anketa_raqami: anketa, vafot_sanasi: sana }),
      });
      const result = await r.json();
      if (result.xato) { alert('Xato: ' + result.xato); return; }
      overlay.remove();
      await ekranniOchish('vafot');
    });
  });
}

// ---------------- PORTFEL ----------------
async function portfelniYuklash(main) {
  main.innerHTML = `
    <div class="page-title">Portfel ma'lumotlarini import qilish</div>
    <div class="page-sub">IFRS portfel hisobotini (.xlsb) yuklang. Mavjud kreditlar yangilanadi, yangilari qo'shiladi — avval yaratilgan xatlar/Davo arizalar bilan bog'lanish saqlanib qoladi.</div>

    <div class="card">
      <div class="card-h">Import</div>
      <div class="btn-row">
        <button class="btn-gold" id="pf-import-btn" style="margin-left:0;">📂 .xlsb faylni tanlash va import qilish</button>
        <input type="file" id="pf-file-input" accept=".xlsb" style="display:none;">
      </div>
      <div id="pf-status" style="margin-top:10px; font-size:12.5px; color:var(--muted);"></div>
    </div>

    <div style="height:16px;"></div>
    <div class="card-h" style="margin-bottom:10px;">45+ kun muddati o'tgan mijozlar (ko'rinish)</div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr><th>Anketa №</th><th>Mijoz nomi</th><th>Turi</th><th>DPD</th><th>Muddati o'tgan qarz</th></tr></thead>
          <tbody id="pf-tbody"><tr><td colspan="5" class="loading">Yuklanmoqda...</td></tr></tbody>
        </table>
      </div>
    </div>
  `;
  document.getElementById('pf-import-btn').addEventListener('click', () => document.getElementById('pf-file-input').click());
  document.getElementById('pf-file-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    document.getElementById('pf-status').textContent = 'Import qilinmoqda... (katta fayllar 20-30 sekund olishi mumkin)';
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch(`${API_BASE}/portfel/import`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { document.getElementById('pf-status').textContent = 'Xato: ' + data.xato; return; }
    let msg = `Tayyor! ${data.jami_qator} ta qator yangilandi. Joriy faol portfel: ${data.faol_soni} ta kredit.`;
    if (data.faolsiz_soni) msg += ` (${data.faolsiz_soni} ta eski kredit bu faylda endi yo'q.)`;
    if (data.avtomatik_tozalangan) msg += ` ${data.avtomatik_tozalangan} ta ish qarzdorlik pasaygani sababli avtomatik yakunlandi.`;
    document.getElementById('pf-status').textContent = msg;
    e.target.value = '';
    await portfelJadvalniYuklash();
  });
  await portfelJadvalniYuklash();
}

async function portfelJadvalniYuklash() {
  const data = await apiGet('/portfel/royxat');
  document.getElementById('pf-tbody').innerHTML = data.royxat.map(r => `
    <tr><td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.turi}</td><td>${r.dpd}</td><td>${formatSum(r.jami_qarz)}</td></tr>
  `).join('');
}

// ---------------- MIJOZLAR BAZASI ----------------
async function mijozlarBazasiniYuklash(main) {
  const stats = await apiGet('/mijozlar/stats');
  main.innerHTML = `
    <div class="page-title">Mijozlar bazasini import qilish</div>
    <div class="page-sub">Mijozlar bazasi — manzil, telefon va boshqa aloqa ma'lumotlari xatlar va Davo arizalar uchun ishlatiladi.</div>

    <div class="card">
      <div class="card-h">Tavsiya etiladi: xom matn fayli</div>
      <div class="page-sub" style="margin-bottom:10px;">Bank tizimidan '|' bilan ajratilgan xom (.txt yoki .zip) faylni to'g'ridan-to'g'ri yuklang.</div>
      <button class="btn-gold" id="mj-import-btn" style="margin-left:0;">📄 Xom matn (.txt / .zip) faylni import qilish</button>
      <input type="file" id="mj-file-input" accept=".txt,.zip" style="display:none;">
      <div id="mj-status" style="margin-top:10px; font-size:12.5px; color:var(--muted);"></div>
    </div>

    <div style="height:16px;"></div>
    <div class="card">
      <div class="card-h">Muqobil: Excel fayl (ustunlarni o'zingiz moslashtirasiz)</div>
      <div class="btn-row">
        <button class="btn" id="mj-excel-jismoniy">👤 Jismoniy shaxslar Excel faylini import qilish</button>
        <button class="btn" id="mj-excel-yuridik">🏢 Yuridik shaxslar Excel faylini import qilish</button>
        <input type="file" id="mj-excel-file" accept=".xlsx,.xls" style="display:none;">
      </div>
    </div>

    <div style="height:16px;"></div>
    <div class="stat-row">
      <div class="stat-card"><div class="stat-num" id="mj-jis">${formatSum(stats.jismoniy)}</div><div class="stat-label">Jismoniy shaxslar</div></div>
      <div class="stat-card"><div class="stat-num" id="mj-yur">${formatSum(stats.yuridik)}</div><div class="stat-label">Yuridik shaxslar</div></div>
    </div>
  `;
  document.getElementById('mj-import-btn').addEventListener('click', () => document.getElementById('mj-file-input').click());
  document.getElementById('mj-file-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    document.getElementById('mj-status').textContent = 'Import qilinmoqda...';
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch(`${API_BASE}/mijozlar/import_txt`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { document.getElementById('mj-status').textContent = 'Xato: ' + data.xato; return; }
    let msg = `Tayyor! ${data.import_qilingan} / ${data.jami_qator} yozuv import qilindi.`;
    if (data.otkazib_yuborildi) msg += ` (${data.otkazib_yuborildi} ta qator o'tkazib yuborildi.)`;
    document.getElementById('mj-status').textContent = msg;
    e.target.value = '';
    const newStats = await apiGet('/mijozlar/stats');
    document.getElementById('mj-jis').textContent = formatSum(newStats.jismoniy);
    document.getElementById('mj-yur').textContent = formatSum(newStats.yuridik);
  });

  let mjExcelTuri = null;
  document.getElementById('mj-excel-jismoniy').addEventListener('click', () => {
    mjExcelTuri = 'jismoniy';
    document.getElementById('mj-excel-file').click();
  });
  document.getElementById('mj-excel-yuridik').addEventListener('click', () => {
    mjExcelTuri = 'yuridik';
    document.getElementById('mj-excel-file').click();
  });
  document.getElementById('mj-excel-file').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch(`${API_BASE}/mijozlar/excel_ustunlari`, { method: 'POST', body: fd });
    const data = await r.json();
    e.target.value = '';
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    mjUstunMoslashtirishDialogOchish(mjExcelTuri, data.ustunlar, data.namuna);
  });
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
let rejaSubTab = 'kunlik';

async function rejaGrafikniYuklash(main) {
  main.innerHTML = `
    <div class="page-title">Reja Grafik</div>
    <div class="page-sub">Bugungi kunda qilinishi kerak bo'lgan ishlar rejasi (xat, Davo ariza, MIB) va tarmoqlar kesimida bajarilgan ishlar hisoboti.</div>
    <div class="toolbar" style="margin-bottom:0;">
      <button class="btn ${rejaSubTab === 'kunlik' ? 'ghost' : ''}" id="reja-tab-kunlik"
        style="${rejaSubTab === 'kunlik' ? 'background:var(--navy);color:#fff;' : ''}">Kunlik ish rejasi</button>
      <button class="btn ${rejaSubTab === 'sudkunlari' ? 'ghost' : ''}" id="reja-tab-sudkunlari"
        style="${rejaSubTab === 'sudkunlari' ? 'background:var(--navy);color:#fff;' : ''}">⚖ Sud kunlari</button>
    </div>
    <div id="reja-body"></div>
  `;
  document.getElementById('reja-tab-kunlik').addEventListener('click', () => { rejaSubTab = 'kunlik'; rejaGrafikniYuklash(main); });
  document.getElementById('reja-tab-sudkunlari').addEventListener('click', () => { rejaSubTab = 'sudkunlari'; rejaGrafikniYuklash(main); });
  if (rejaSubTab === 'sudkunlari') await sudKunlariBoliminiChizish();
  else await rejaKunlikBoliminiChizish();
}

async function rejaKunlikBoliminiChizish() {
  const body = document.getElementById('reja-body');
  const [kunlik, tarmoqData] = await Promise.all([apiGet('/reja/kunlik'), apiGet('/reja/tarmoq')]);
  body.innerHTML = `
    <div class="card-h" style="margin-bottom:10px;">Bugungi ish rejasi (${kunlik.deadline} gacha, ${kunlik.ish_kunlari_qolgan} ish kuni qoldi)</div>
    <div class="card-row">
      ${kunlik.turkumlar.map(t => `
        <div class="card">
          <div class="card-h">${t.nomi}</div>
          <div style="display:flex; justify-content:space-between; font-size:13px; padding:4px 0;">
            <span>Kunlik reja:</span><b>${t.reja} ta</b></div>
          <div style="display:flex; justify-content:space-between; font-size:13px; padding:4px 0;">
            <span>Bajarildi:</span><b style="color:#1E6B2E;">${t.bajarildi} ta</b></div>
          <div style="display:flex; justify-content:space-between; font-size:13px; padding:4px 0;">
            <span>Qolib ketyapti:</span><b style="color:var(--err);">${t.qoldi} ta</b></div>
        </div>`).join('')}
    </div>

    <div class="card" style="margin-bottom:16px;">
      <div class="card-h">Kunlik ish rejasi umumiy bajarilishi</div>
      <div class="stat-num" style="color:${kunlik.foiz < 30 ? 'var(--err)' : '#1E6B2E'};">${kunlik.foiz}%</div>
      <div class="stat-label">${kunlik.umumiy_bajarildi} / ${kunlik.umumiy_reja} ta bajarildi (jami oy oxirigacha ish: ${kunlik.jami_ish} ta)</div>
    </div>

    <div class="card-h" style="margin-bottom:10px;">Tarmoq kesimida bajarilgan ishlar</div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr><th>Tarmoq</th><th>Jami xat</th><th>Yuborilgan</th><th>Davo ariza</th><th>Sudga o'tkazilgan</th><th>MIBga o'tkazilgan</th></tr></thead>
          <tbody>
            ${tarmoqData.tarmoq.map(r => `<tr>
              <td>${r.tarmoq}</td><td>${r.xat_soni}</td><td>${r.yuborilgan_soni || 0}</td>
              <td>${r.davo_soni || 0}</td><td>${r.sud_soni || 0}</td><td>${r.mib_soni || 0}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

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
              <td>${r.anketa_raqami}</td><td>${r.mijoz_nomi}</td><td>${r.sud_sanasi}</td><td>${r.sud_vaqti}</td>
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
const MIB_SOZLAMA_FIELDS = [
  ['mib_harakatsizlik_muddati_kun', "MIBda harakatsizlik ogohlantirish muddati (kun)"],
  ['bxm_miqdori', "BXM (bazaviy hisoblash miqdori), so'm"],
  ['mib_toxtatish_dpd_chegara', "MIB to'xtatish uchun DPD chegarasi (kun)"],
];
const VAFOT_SOZLAMA_FIELDS = [
  ['sugurta_javob_muddati_ish_kun', "Sug'urta javobini kutish muddati (ish kuni)"],
];
const UMUMIY_SOZLAMA_FIELDS = [
  ['hujjatlar_papkasi', "Yaratilgan hujjatlar saqlanadigan papka (masalan D:\\Qarz Nazorat\\Hujjatlar) — bo'sh qoldirilsa standart joy ishlatiladi"],
];

async function sozlamalarEkraniniQurish(container, sarlavha, fields, qoshimchaHtml) {
  const current = await apiGet('/sozlamalar');
  container.innerHTML = `
    <div class="page-title" style="font-size:19px;">${sarlavha}</div>
    <div class="card" style="max-width:720px;">
      <div id="soz-fields"></div>
      <button class="btn-gold" id="soz-save" style="margin-left:0; margin-top:14px;">💾 Saqlash</button>
      <div id="soz-status" style="margin-top:8px; font-size:12.5px; color:#1E6B2E;"></div>
    </div>
    ${qoshimchaHtml || ''}
  `;
  const fieldsWrap = container.querySelector('#soz-fields');
  fieldsWrap.innerHTML = fields.map(([key, label]) => `
    <div style="margin-bottom:10px;">
      <label style="display:block; font-size:12.5px; color:var(--muted); margin-bottom:4px;">${label}</label>
      <input class="tb-input" style="width:100%;" data-key="${key}" value="${(current[key] || '').toString().replace(/"/g, '&quot;')}">
    </div>
  `).join('');
  container.querySelector('#soz-save').addEventListener('click', async () => {
    const data = {};
    fieldsWrap.querySelectorAll('input[data-key]').forEach(inp => { data[inp.dataset.key] = inp.value; });
    await fetch(`${API_BASE}/sozlamalar`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    });
    container.querySelector('#soz-status').textContent = "✓ Saqlandi";
    setTimeout(() => { container.querySelector('#soz-status').textContent = ''; }, 2500);
  });
}

async function foydalanuvchilarBoliminiChizish(container) {
  const data = await apiGet('/foydalanuvchilar');
  container.innerHTML = `
    <div class="card" style="max-width:720px;">
      <div class="card-h">Tarmoq foydalanuvchilari</div>
      <div class="page-sub" style="margin:0 0 12px;">
        Bir nechta kompyuterni bitta umumiy bazaga ulash uchun, har bir kompyuter/xodim uchun alohida login va parol yarating.
        Bu ro'yxat bo'sh bo'lsa, tizim eski (yagona parol) rejimida ishlashda davom etadi.
      </div>
      <div class="btn-row" style="margin-bottom:14px;">
        <input class="tb-input" id="fy-login" placeholder="Login (masalan: kompyuter1)" style="width:160px;">
        <input class="tb-input" id="fy-ism" placeholder="F.I.Sh (ixtiyoriy)" style="width:160px;">
        <input class="tb-input" id="fy-parol" type="text" placeholder="Parol (kamida 4 belgi)" style="width:150px;">
        <button class="btn-gold" id="fy-qoshish" style="margin-left:0;">+ Qo'shish</button>
      </div>
      <table style="width:100%; font-size:12.5px;">
        <thead><tr style="text-align:left; color:var(--muted);"><th>Login</th><th>F.I.Sh</th><th>Holati</th><th></th></tr></thead>
        <tbody id="fy-tbody">
          ${data.royxat.map(u => `<tr>
            <td style="padding:6px 0;">${u.login}</td><td>${u.toliq_ism || '—'}</td>
            <td>${u.faol ? '✓ Faol' : '✕ O\'chirilgan'}</td>
            <td>
              <button class="btn" data-id="${u.id}" data-act="fy-toggle" style="padding:3px 8px; font-size:11.5px;">${u.faol ? 'O\'chirish' : 'Yoqish'}</button>
              <button class="btn danger" data-id="${u.id}" data-act="fy-delete" style="padding:3px 8px; font-size:11.5px;">🗑</button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
      <div id="fy-status" style="margin-top:10px; font-size:12.5px; color:var(--err);"></div>
    </div>
  `;
  document.getElementById('fy-qoshish').addEventListener('click', async () => {
    const login = document.getElementById('fy-login').value.trim();
    const toliq_ism = document.getElementById('fy-ism').value.trim();
    const parol = document.getElementById('fy-parol').value;
    const r = await fetch(`${API_BASE}/foydalanuvchilar`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login, toliq_ism, parol }),
    });
    const res = await r.json();
    if (res.xato) { document.getElementById('fy-status').textContent = res.xato; return; }
    await foydalanuvchilarBoliminiChizish(container);
  });
  container.querySelectorAll('[data-act="fy-toggle"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const faolHozir = btn.textContent.trim() === "O'chirish";
      await fetch(`${API_BASE}/foydalanuvchilar/${btn.dataset.id}/faollik`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ faol: !faolHozir }),
      });
      await foydalanuvchilarBoliminiChizish(container);
    });
  });
  container.querySelectorAll('[data-act="fy-delete"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm("Bu foydalanuvchini butunlay o'chirasizmi?")) return;
      await fetch(`${API_BASE}/foydalanuvchilar/${btn.dataset.id}`, { method: 'DELETE' });
      await foydalanuvchilarBoliminiChizish(container);
    });
  });
}

function shablonBolimiHtml(sarlavha, tavsif, turi, davoTurlariOptions) {
  const davoQismi = turi === 'davo' ? `
    <div style="margin-bottom:10px;">
      <label style="display:block; font-size:12.5px; color:var(--muted); margin-bottom:4px;">Ariza turi</label>
      <select class="tb-select" id="sh-${turi}-davoturi" style="width:100%; max-width:400px;">${davoTurlariOptions}</select>
    </div>` : '';
  return `
    <div class="card" style="max-width:720px; margin-top:16px;">
      <div class="card-h">${sarlavha}</div>
      <div class="page-sub" style="margin:0 0 12px;">${tavsif}</div>
      ${davoQismi}
      <div class="btn-row">
        <button class="btn" id="sh-${turi}-korish">📄 Joriy shablonni ko'rish</button>
        <button class="btn-gold" id="sh-${turi}-yuklash" style="margin-left:0;">📤 Yangi shablon yuklash (.docx)</button>
        <input type="file" id="sh-${turi}-file" accept=".docx" style="display:none;">
      </div>
      <div id="sh-${turi}-status" style="margin-top:8px; font-size:12.5px; color:#1E6B2E;"></div>
    </div>
  `;
}

function shablonBolimiIshga(container, turi) {
  const korishBtn = container.querySelector(`#sh-${turi}-korish`);
  const yuklashBtn = container.querySelector(`#sh-${turi}-yuklash`);
  const fileInput = container.querySelector(`#sh-${turi}-file`);
  if (!korishBtn) return;

  const davoTuriOlish = () => turi === 'davo' ? container.querySelector(`#sh-${turi}-davoturi`).value : null;

  korishBtn.addEventListener('click', () => {
    const davoTuri = davoTuriOlish();
    let url = `${API_BASE}/shablon/korish?turi=${turi}`;
    if (davoTuri) url += `&davo_turi=${davoTuri}`;
    window.open(url, '_blank');
  });

  yuklashBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append('turi', turi);
    const davoTuri = davoTuriOlish();
    if (davoTuri) fd.append('davo_turi', davoTuri);
    fd.append('file', f);
    const r = await fetch(`${API_BASE}/shablon/yuklash`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    e.target.value = '';

    if (turi === 'xat' || turi === 'davo') {
      const qaytaTayyorlash = confirm(
        "Shablon yangilandi.\n\nHali yuborilmagan/olib kelinmagan hujjatlarni yangi shablon bilan hozir qayta tayyorlaymi?"
      );
      if (qaytaTayyorlash) {
        const body = { turi };
        if (davoTuri) body.davo_turi = davoTuri;
        const r2 = await fetch(`${API_BASE}/shablon/qayta_tayyorlash`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        });
        const data2 = await r2.json();
        container.querySelector(`#sh-${turi}-status`).textContent =
          `✓ Shablon yangilandi. ${data2.yangilandi} ta hujjat qayta tayyorlandi.${data2.xatolar && data2.xatolar.length ? ' (' + data2.xatolar.length + ' ta xato)' : ''}`;
      } else {
        container.querySelector(`#sh-${turi}-status`).textContent = "✓ Shablon yangilandi.";
      }
    } else {
      container.querySelector(`#sh-${turi}-status`).textContent = "✓ Shablon yangilandi.";
    }
  });
}

function xavfsizlikBolimiHtml() {
  return `
    <div class="card" style="max-width:720px; margin-top:16px;">
      <div class="card-h">Xavfsizlik — parolni o'zgartirish</div>
      <label style="display:block; font-size:12.5px; color:var(--muted); margin-bottom:4px;">Yangi parol</label>
      <input type="password" class="tb-input" id="xv-parol" style="width:100%; max-width:280px;">
      <button class="btn" id="xv-save" style="margin-top:10px;">Parolni o'rnatish</button>
      <div id="xv-status" style="margin-top:8px; font-size:12.5px; color:#1E6B2E;"></div>
    </div>
  `;
}

function xavfsizlikBolimiIshga(container) {
  const btn = container.querySelector('#xv-save');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const parol = container.querySelector('#xv-parol').value.trim();
    if (!parol) { alert('Yangi parolni kiriting.'); return; }
    await fetch(`${API_BASE}/sozlamalar/parol`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ yangi_parol: parol }),
    });
    container.querySelector('#xv-status').textContent = "✓ Parol o'rnatildi";
    container.querySelector('#xv-parol').value = '';
  });
}

async function umumiySozlamalarniYuklash(main) {
  let joriyBolim = 'talabnoma';
  const bolimlar = {
    talabnoma: { nomi: 'Talabnoma', fields: TALABNOMA_SOZLAMA_FIELDS },
    davo: { nomi: 'Davo ariza', fields: DAVO_ARIZA_SOZLAMA_FIELDS },
    sud: { nomi: 'Sud Ishlari', fields: [] },
    mib: { nomi: 'MIB', fields: MIB_SOZLAMA_FIELDS },
    vafot: { nomi: 'Vafot etganlar', fields: VAFOT_SOZLAMA_FIELDS },
    umumiy: { nomi: "Hujjatlar joyi va xavfsizlik", fields: UMUMIY_SOZLAMA_FIELDS },
    foydalanuvchilar: { nomi: "Foydalanuvchilar (tarmoq)", fields: [] },
  };

  async function chizish() {
    main.innerHTML = `
      <div class="page-title">Sozlamalar</div>
      <div style="display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap;">
        ${Object.entries(bolimlar).map(([k, v]) => `
          <button class="btn" data-bolim="${k}" style="${k === joriyBolim ? 'background:var(--navy);color:#fff;' : ''}">${v.nomi}</button>
        `).join('')}
      </div>
      <div id="soz-container"></div>
    `;
    main.querySelectorAll('[data-bolim]').forEach(btn => {
      btn.addEventListener('click', () => { joriyBolim = btn.dataset.bolim; chizish(); });
    });
    const container = document.getElementById('soz-container');
    const b = bolimlar[joriyBolim];
    if (joriyBolim === 'foydalanuvchilar') {
      await foydalanuvchilarBoliminiChizish(container);
      return;
    }
    let qoshimcha = '';
    if (joriyBolim === 'umumiy') qoshimcha = xavfsizlikBolimiHtml();
    else if (joriyBolim === 'talabnoma') qoshimcha = shablonBolimiHtml(
      "Xat shabloni (Word)", "Yangi shablon yuklasangiz, hali yuborilmagan ('Tayyor' holatidagi) xatlar avtomatik shu yangi shablon bilan qayta tayyorlanadi.", 'xat');
    else if (joriyBolim === 'vafot') qoshimcha = shablonBolimiHtml(
      "Sug'urta xabarnomasi shabloni (Word)", "Vafot etgan mijozlar bo'yicha sug'urta kompaniyasiga yuboriladigan xabarnoma shabloni.", 'sugurta');
    else if (joriyBolim === 'mib') qoshimcha = shablonBolimiHtml(
      "Yig'ma jild tituli shabloni (Word)", "MIBga o'tkazish tasdiqlanganda avtomatik yaratiladigan yig'ma jild muqova hujjati shabloni.", 'yigma_jild');
    else if (joriyBolim === 'davo') {
      const davoTurlariData = await apiGet('/shablon/davo_turlari');
      const options = Object.entries(davoTurlariData.turlari).map(([k, v]) => `<option value="${k}">${v}</option>`).join('');
      qoshimcha = shablonBolimiHtml(
        "Davo ariza shablonlari (Word)",
        "Ariza turini tanlab, uning shablonini yangilashingiz mumkin. Yangilagach, shu turdagi, hali 'Olib kelindi' deb belgilanmagan arizalarni qayta tayyorlash so'raladi.",
        'davo', options);
      qoshimcha += shablonBolimiHtml(
        "SSPga reestr shabloni (Word)",
        "Davo Ariza bo'limida 'SSPga Reestr tayyorlash' tugmasi bosilganda ishlatiladigan jadval shabloni.",
        'reestr_ssp');
    }
    else if (joriyBolim === 'sud') {
      qoshimcha = shablonBolimiHtml(
        "Sud harakatlari yig'ma jildi tituli shabloni (Word)",
        "Sud harakatlari yig'ma jildi yaratilganda ishlatiladigan muqova (titul) hujjati shabloni.",
        'sud_yigma_jild');
      qoshimcha += shablonBolimiHtml(
        "Ma'lumotnoma (sudga topshirishda) shabloni (Word)",
        "Davo ariza sudga topshirilayotganda tayyorlanadigan qarzdorlik ma'lumotnomasi shabloni.",
        'malumotnoma_topshirishda');
      qoshimcha += shablonBolimiHtml(
        "Ma'lumotnoma (sud kuni) shabloni (Word)",
        "Sud kunidan 1 kun oldin tayyorlanadigan, qarzdorlik o'zgarishini solishtiruvchi ma'lumotnoma shabloni.",
        'malumotnoma_kun');
    }
    await sozlamalarEkraniniQurish(container, `${b.nomi} sozlamalari`, b.fields, qoshimcha);
    if (joriyBolim === 'umumiy') xavfsizlikBolimiIshga(container);
    else if (['talabnoma', 'vafot', 'mib'].includes(joriyBolim)) shablonBolimiIshga(container, { talabnoma: 'xat', vafot: 'sugurta', mib: 'yigma_jild' }[joriyBolim]);
    else if (joriyBolim === 'davo') { shablonBolimiIshga(container, 'davo'); shablonBolimiIshga(container, 'reestr_ssp'); }
    else if (joriyBolim === 'sud') {
      shablonBolimiIshga(container, 'sud_yigma_jild');
      shablonBolimiIshga(container, 'malumotnoma_topshirishda');
      shablonBolimiIshga(container, 'malumotnoma_kun');
    }
    if (joriyBolim === 'mib') {
      await mibHarakatTurlariBolimiChizish(container);
    }
  }
  await chizish();
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
          <td style="padding:4px 0;">${t.nomi}</td>
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

function vafotSugurtaDialogOchish(vafotId, polisHolati) {
  if (polisHolati !== 'amalda') { alert("Sug'urta polisi amalda emas — sug'urta ma'lumoti kiritilmaydi."); return; }
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:400px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Sug'urta ma'lumotini kiritish</div>
      <label style="display:block;margin-bottom:8px;">Sug'urta kompaniyasi<br><input class="tb-input" id="vs-kompaniya" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Polis raqami<br><input class="tb-input" id="vs-raqam" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Polis fayli (ixtiyoriy)<br><input type="file" id="vs-fayl"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="vs-cancel">Bekor qilish</button>
        <button class="btn-gold" id="vs-save" style="margin-left:0;">✓ Saqlash</button>
      </div>
    </div>`);
  overlay.querySelector('#vs-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#vs-save').addEventListener('click', async () => {
    const fd = new FormData();
    fd.append('id', vafotId);
    fd.append('kompaniya', overlay.querySelector('#vs-kompaniya').value.trim());
    fd.append('raqam', overlay.querySelector('#vs-raqam').value.trim());
    const f = overlay.querySelector('#vs-fayl').files[0];
    if (f) fd.append('polis_fayl', f);
    const r = await fetch(`${API_BASE}/vafot/sugurta_kiritish`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    await ekranniOchish('vafot');
  });
}

async function vafotXabarnomaTayyorlash(vafotId) {
  const r = await fetch(`${API_BASE}/vafot/xabarnoma_tayyorlash?id=${vafotId}`);
  if (!r.ok) {
    const data = await r.json();
    alert('Xato: ' + (data.xato || 'Nomalum xato'));
    return;
  }
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'xabarnoma.docx'; a.click();
  URL.revokeObjectURL(url);
  alert('Xabarnoma tayyorlandi. Yuborilgach, "✓ Yuborildi" tugmasini bosing.');
}

function vafotXabYuborildiDialog(vafotId, mijozNomi) {
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:380px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Xabarnoma yuborilgan sana — ${mijozNomi}</div>
      <label style="display:block;margin-bottom:8px;">Sana (kun.oy.yil)<br><input class="tb-input" id="vy-sana" style="width:100%;"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="vy-cancel">Bekor qilish</button>
        <button class="btn-gold" id="vy-save" style="margin-left:0;">✓ Saqlash</button>
      </div>
    </div>`);
  overlay.querySelector('#vy-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#vy-save').addEventListener('click', async () => {
    const sana = overlay.querySelector('#vy-sana').value.trim();
    if (!sana) { alert('Sanani kiriting.'); return; }
    const r = await fetch(`${API_BASE}/vafot/xabarnoma_yuborildi`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: vafotId, sana }),
    });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    await ekranniOchish('vafot');
  });
}

function vafotJavobKeldiDialog(vafotId, mijozNomi) {
  const overlay = mibOverlayOchish(`
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:380px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Sug'urta javobi kelgan sana — ${mijozNomi}</div>
      <label style="display:block;margin-bottom:8px;">Sana (kun.oy.yil)<br><input class="tb-input" id="vj-sana" style="width:100%;"></label>
      <label style="display:block;margin-bottom:8px;">Javob xati (ixtiyoriy)<br><input type="file" id="vj-fayl"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="vj-cancel">Bekor qilish</button>
        <button class="btn-gold" id="vj-save" style="margin-left:0;">✓ Saqlash</button>
      </div>
    </div>`);
  overlay.querySelector('#vj-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#vj-save').addEventListener('click', async () => {
    const sana = overlay.querySelector('#vj-sana').value.trim();
    if (!sana) { alert('Sanani kiriting.'); return; }
    const fd = new FormData();
    fd.append('id', vafotId);
    fd.append('sana', sana);
    const f = overlay.querySelector('#vj-fayl').files[0];
    if (f) fd.append('fayl', f);
    const r = await fetch(`${API_BASE}/vafot/javob_keldi`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    await ekranniOchish('vafot');
  });
}

function vafotFaylDialogOchish(vafotId) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:20px 24px;width:380px;">
      <div style="font-size:16px;font-weight:700;margin-bottom:14px;">Hujjat yuklash</div>
      <label style="display:block;margin-bottom:8px;">Hujjat turi<br>
        <select class="tb-select" id="vf-turi" style="width:100%;">
          <option value="olimlik">O'limlik guvohnomasi</option>
          <option value="pasport">Pasport</option>
          <option value="sugurta_polis">Sug'urta polisi</option>
        </select></label>
      <label style="display:block;margin-bottom:8px;">Fayl<br><input type="file" id="vf-file"></label>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" id="vf-cancel">Bekor qilish</button>
        <button class="btn-gold" id="vf-save" style="margin-left:0;">✓ Yuklash</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  document.getElementById('vf-cancel').addEventListener('click', () => overlay.remove());
  document.getElementById('vf-save').addEventListener('click', async () => {
    const f = document.getElementById('vf-file').files[0];
    if (!f) { alert('Faylni tanlang.'); return; }
    const fd = new FormData();
    fd.append('id', vafotId);
    fd.append('turi', document.getElementById('vf-turi').value);
    fd.append('file', f);
    const r = await fetch(`${API_BASE}/vafot/fayl_yuklash`, { method: 'POST', body: fd });
    const data = await r.json();
    if (data.xato) { alert('Xato: ' + data.xato); return; }
    overlay.remove();
    await ekranniOchish('vafot');
  });
}

// ---------------- ISHGA TUSHIRISH ----------------
window.addEventListener('DOMContentLoaded', async () => {
  if (window.qarzNazorat) {
    const konfig = await window.qarzNazorat.tarmoqSozlamasiniOlish();
    if (konfig && konfig.server_ip) {
      // MIJOZ rejimi — boshqa (server) kompyuterdagi backend'ga ulanamiz.
      API_BASE = `http://${konfig.server_ip}:8877/api`;
    } else {
      const port = await window.qarzNazorat.getBackendPort();
      API_BASE = `http://127.0.0.1:${port}/api`;
    }
  }
  await loginOqimi();
});

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
  sidebarQurish();
  ekranniOchish('bosh_sahifa');
}
