// MIB ijro harakatlari ekrani.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

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
    faylniYuklabOlish(`${API_BASE}/mib/tolovlar_shablon?manba=kunlik_29801`);
  });
  document.getElementById('tm-shablon').addEventListener('click', () => {
    faylniYuklabOlish(`${API_BASE}/mib/tolovlar_shablon?manba=mib`);
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
        <div style="font-weight:600;">${n.anketa_raqami} — ${xavfsizMatn(n.mijoz_nomi)}</div>
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
          <div style="font-weight:600;">${n.anketa_raqami} — ${xavfsizMatn(n.mijoz_nomi)}</div>
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
                <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td>
                <td>${formatSum(r.jami_qarz)}</td><td>${r.mib_ish_raqami}</td><td>${r.harakatsizlik_kun}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
    document.getElementById('mib-harakatsiz-excel').addEventListener('click', () => {
      faylniYuklabOlish(`${API_BASE}/mib/harakatsizlar_excel`);
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
      faylniYuklabOlish(`${API_BASE}/mib/otkazish_kerak_excel`);
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
              <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td>
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
      faylniYuklabOlish(`${API_BASE}/mib/avtomashinalar_xatlanmagan_excel`);
    });
    document.getElementById('mib-jarayon-excel').addEventListener('click', () => {
      faylniYuklabOlish(`${API_BASE}/mib/jarayondagilar_excel`);
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
              <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td>
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
            : turlarData.turlar.map(t => `<option value="${xavfsizMatn(t.nomi)}">${xavfsizMatn(t.nomi)}</option>`).join('')}
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
                <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td>
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
