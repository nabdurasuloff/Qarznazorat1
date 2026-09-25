// Portfel va Mijozlar bazasi ekranlari.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

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
    <tr><td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td><td>${r.dpd}</td><td>${formatSum(r.jami_qarz)}</td></tr>
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
