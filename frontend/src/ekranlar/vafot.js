// Vafot etgan mijozlar ekrani.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

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
              <td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.vafot_sanasi}</td>
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
                ${r.xabarnoma_holati === 'kerak' && r.sugurta_kompaniya ? `<button class="btn" data-id="${r.id}" data-mijoz="${xavfsizMatn(r.mijoz_nomi)}" data-act="vafot-xab-yuborildi">✓ Yuborildi</button>` : ''}
                ${r.xabarnoma_holati === 'yuborildi' ? `<button class="btn" data-id="${r.id}" data-mijoz="${xavfsizMatn(r.mijoz_nomi)}" data-act="vafot-javob-keldi">✓ Javob keldi</button>` : ''}
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
    faylniYuklabOlish(`${API_BASE}/vafot/excel`);
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
