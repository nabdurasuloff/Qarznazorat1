// 95413 (balansdan chiqarilgan kreditlar) ekrani.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

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
    faylniYuklabOlish(`${API_BASE}/nazorat95413/excel_eksport`);
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
          <td style="padding:5px 0;">${xavfsizMatn(h.hujjat_nomi)}</td>
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
