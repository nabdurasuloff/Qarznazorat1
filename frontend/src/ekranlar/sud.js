// SUD ishlari ekrani.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

// ---------------- SUD ISHLARI ----------------
let sudSubTab = 'topshirish';

let sudBelgilangan = new Set();

let sudTopshirishCache = [];

let sudRoyxatCache = [];

// ---------------- BIZNES-HAMROH.UZ ----------------
// Davo arizalar endi SSPga qo'lda emas, biznes-hamroh.uz portali orqali
// ELEKTRON yuboriladi. Bu bo'lim portalga kiritiladigan barcha
// ma'lumotlarni tayyorlab beradi va murojaat holatini kuzatadi.

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
    ${data.iqtisodiy_sud ? `
      <div class="card" style="margin-bottom:12px; padding:8px 12px; background:#FFF8E6; border-left:3px solid var(--gold);">
        <div style="font-size:12px;">⚖ <b>Iqtisodiy sud.</b> Davo ariza va Talabnoma nusxalari
        taraflarga (javobgar, kafil, garov ta'minlovchi) yuborilgani tasdiqlanishi
        <b>majburiy</b> — pochta kvitansiyasi yoki topshirish xabarnomasini yuklang.
        Bu hujjatlarsiz sudga yuborishga ruxsat berilmaydi.</div>
      </div>` : ''}
    <table style="width:100%; font-size:12.5px; table-layout:fixed;">
      <thead><tr style="text-align:left; color:var(--muted);">
        <th style="width:40%;">Hujjat</th><th style="width:37%;">Holati</th><th style="width:23%;"></th></tr></thead>
      <tbody>
        ${data.hujjatlar.map(h => `<tr>
          <td style="padding:6px 0;">${xavfsizMatn(h.nomi)}${h.sana_soraladi ? ' <span style="color:var(--err);">*</span>' : ''}</td>
          <td>${h.mavjud
            ? `✓ Yuklangan${h.sana ? ` (${h.sana})` : ''} &nbsp; <a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(h.fayl)}" target="_blank">👁 Ko'rish</a>`
            : "— Yo'q"}</td>
          <td style="text-align:right; white-space:nowrap;">${h.tizim_yaratadi ? `
            <button class="btn-gold" data-rasmiy="${h.tizim_yaratadi}" style="padding:3px 10px; font-size:11.5px; margin-left:0;">
              ${h.mavjud ? '🔄 Qayta yaratish' : '📄 Yaratish'}</button>`
            : !['Titul', 'Davo ariza', 'Xat'].includes(h.nomi) ? `
            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:3px;">
              ${h.sana_soraladi ? `<input class="tb-input" id="syj-sana-${h.maydon}" placeholder="Yuborilgan sana"
                value="${h.sana || ''}" title="Taraflarga yuborilgan sana (kk.oo.yyyy)"
                style="width:110px; font-size:11px; padding:2px 5px;">` : ''}
              <input type="file" id="syj-file-${h.maydon}" accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff,.docx" style="display:none;">
              <button class="btn" data-maydon="${h.maydon}" data-act="syj-upload" style="padding:3px 10px; font-size:11.5px;">📤 Yuklash</button>
            </div>` : ''}
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
    ${!data.toliqmi ? `<div class="page-sub" style="color:var(--err); margin-top:8px;">
      Ruxsat berish uchun barcha hujjatlar to'liq yuklanishi kerak. Yetishmayapti:
      ${data.hujjatlar.filter(h => !h.mavjud && h.majburiy !== false).map(h => h.nomi).join(', ') || '—'}</div>` : ''}
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
    const sanaInput = content.querySelector(`#syj-sana-${btn.dataset.maydon}`);
    btn.addEventListener('click', () => {
      // MUHIM: taraflarga yuborilganlik tasdig'i uchun SANA ham majburiy —
      // fayl tanlash oynasini ochishdan oldin tekshiramiz, aks holda
      // foydalanuvchi faylni tanlab bo'lgach xato chiqib, qaytadan
      // boshlashga to'g'ri kelardi.
      if (sanaInput && !sanaInput.value.trim()) {
        alert("Avval taraflarga yuborilgan sanani kiriting (kk.oo.yyyy).");
        sanaInput.focus();
        return;
      }
      fileInput.click();
    });
    fileInput.addEventListener('change', async () => {
      const f = fileInput.files[0];
      if (!f) return;
      const fd = new FormData();
      fd.append('anketa_raqami', anketa);
      fd.append('maydon', btn.dataset.maydon);
      fd.append('file', f);
      if (sanaInput) fd.append('yuborilgan_sana', sanaInput.value.trim());
      const res = await fetch(`${API_BASE}/sud/hujjat_yuklash`, { method: 'POST', body: fd });
      const d = await res.json();
      if (d.xato) { alert('Xato: ' + d.xato); return; }
      await sudYigmaJildModalniChizish(anketa, overlay);
    });
  });
  // Sudga beriladigan rasmiy ma'lumotnomalarni tizim o'zi tayyorlaydi
  content.querySelectorAll('[data-rasmiy]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const turi = btn.dataset.rasmiy;
      const eskiMatn = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Tayyorlanmoqda...';
      try {
        const res = await fetch(`${API_BASE}/sud/rasmiy_malumotnoma_yaratish`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ anketa_raqami: anketa, turi }),
        });
        const d = await res.json();
        if (d.xato) { alert('Xato: ' + d.xato); btn.disabled = false; btn.textContent = eskiMatn; return; }
        if (d.ogohlantirish) alert('Diqqat!\n\n' + d.ogohlantirish);
        await sudYigmaJildModalniChizish(anketa, overlay);
      } catch (e) {
        alert("Serverga ulanishda xato: " + e.message);
        btn.disabled = false;
        btn.textContent = eskiMatn;
      }
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
              <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td>
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
              <td>${x.anketa_raqami}</td><td>${xavfsizMatn(x.mijoz_nomi)}</td><td>${x.pinfl_yoki_stir || '—'}</td>
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
    faylniYuklabOlish(`${API_BASE}/sud/xarajatlar_shablon`);
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
      const ishRaqami = await matnSorash('MIB ijro ish raqami', '',
        "Xarajat bo'yicha ochilgan ijro ishining raqamini kiriting.");
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
                <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td>
                <td>${xavfsizMatn(r.sababi_nomi)}</td><td>${r.sana}</td>
                <td>${r.xodim_ism ? `${xavfsizMatn(r.xodim_ism)} — ${r.izoh || ''}` : (r.izoh || '—')}</td>
                <td>
                  ${r.mijoz_arizasi_pdf ? `<a href="#" data-fayl="${xavfsizMatn(r.mijoz_arizasi_pdf)}" data-act="fayl-ochish">📄 Ariza</a>` : ''}
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
      faylniYuklabOlish(`${API_BASE}/sud/kiritilmagan_excel`);
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
              <th>Anketa №</th><th>Mijoz</th><th>Turi</th><th>Qarzdorlik</th>
              <th>Joriy bosqich</th>
              <th>Ariza yaratilgan</th><th>Necha kun kutildi</th>
              <th>Murojaat / ish raqami</th><th>Tasdiqlangan sana</th><th>Holati</th>
              <th>Sud ish raqami</th><th>Sudga topshirilgan</th><th>Sud holati</th>
            </tr></thead>
            <tbody>
              ${data.royxat.map(r => `<tr>
                <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.mijoz_turi}</td>
                <td>${formatSum(r.jami_qarz)}</td>
                <td style="font-weight:600;">${r.joriy_bosqich}</td>
                <td>${r.yaratilgan}</td><td>${r.kutilgan_kun}</td>
                <td>${r.ish_raqami}</td><td>${r.imzo_sana}</td><td>${davoHolatPill(r.holat_pill, r.holati)}</td>
                <td>${r.sud_ish_raqami}</td><td>${r.sud_sana}</td><td>${r.sud_holati}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
    document.getElementById('sh-excel').addEventListener('click', () => {
      faylniYuklabOlish(`${API_BASE}/davo-ariza/hisobot_excel`);
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
        <button class="btn" id="sud-ruxsat-export">✓ Ruxsat berilganlar (Excel)</button>
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
    document.getElementById('sud-ruxsat-export').addEventListener('click', () => {
      tayyorJildYuklabOlish(`${API_BASE}/sud/ruxsat_berilganlar_excel`);
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

function sudTopshirishJadvalniChizish() {
  const tbody = document.getElementById('sud-tbody');
  tbody.innerHTML = sudTopshirishCache.map(r => {
    const checked = sudBelgilangan.has(r.anketa_raqami);
    return `<tr>
      <td><span class="checkbox ${checked ? 'checked' : ''}" data-anketa="${r.anketa_raqami}"></span></td>
      <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td><td>${r.sud_nomi}</td>
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
              <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td>
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
