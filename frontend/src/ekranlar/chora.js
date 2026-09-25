// Chora ko'rish ekrani.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

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
    faylniYuklabOlish(`${API_BASE}/chora/excel_eksport`);
  });
  document.getElementById('chora-sud-excel').addEventListener('click', () => {
    faylniYuklabOlish(`${API_BASE}/davo-ariza/sudga_topshirilganlar_excel`);
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
      <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td><td>${r.dpd}</td>
      <td>${formatSum(r.qarzdorlik)}</td><td>${r.chora_nomi}</td><td>${xavfsizMatn(r.tafsilot)}</td>
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
