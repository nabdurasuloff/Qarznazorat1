// Biznes-hamroh.uz portali ekrani.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

// ---------------- BIZNES-HAMROH.UZ ----------------
// Davo arizalar endi SSPga qo'lda emas, biznes-hamroh.uz portali orqali
// ELEKTRON yuboriladi. Bu bo'lim portalga kiritiladigan barcha
// ma'lumotlarni tayyorlab beradi va murojaat holatini kuzatadi.

let bhHolatFiltr = '';

let bhQidiruv = '';

async function biznesHamrohniYuklash(main) {
  main.innerHTML = `
    <div class="page-title">Biznes-hamroh.uz</div>
    <div class="page-sub">Davo arizalarni biznes-hamroh.uz portali orqali elektron yuborish va murojaat holatini kuzatish.</div>
    <div id="bh-body"><div class="loading">Yuklanmoqda...</div></div>
  `;
  await bhRoyxatniChizish();
}

async function bhRoyxatniChizish() {
  const body = document.getElementById('bh-body');
  const data = await apiGet('/bh/royxat');
  window._bhCache = data.royxat;

  let royxat = data.royxat;
  if (bhHolatFiltr) royxat = royxat.filter(r => r.holati === bhHolatFiltr);

  const kartalar = Object.entries(data.holat_nomlari).map(([kod, nomi]) => {
    const soni = data.soni[kod] || 0;
    const faol = bhHolatFiltr === kod;
    return `<button class="btn ${faol ? '' : 'ghost'}" data-bh-filtr="${kod}"
      style="${faol ? 'background:var(--navy);color:#fff;' : ''}">${nomi}: ${soni}</button>`;
  }).join('');

  if (bhQidiruv) {
    const q = bhQidiruv.toLowerCase();
    royxat = royxat.filter(r => String(r.anketa_raqami).toLowerCase().includes(q)
      || String(r.mijoz_nomi).toLowerCase().includes(q));
  }

  body.innerHTML = `
    <div class="toolbar">
      <input class="tb-input" id="bh-qidiruv" placeholder="Anketa raqami yoki mijoz nomi"
        style="width:230px;" value="${bhQidiruv}">
      <button class="btn" id="bh-qidir">🔍 Topish</button>
      ${bhQidiruv ? '<button class="btn ghost" id="bh-qidiruv-tozalash">✕ Tozalash</button>' : ''}
      <button class="btn-gold" id="bh-excel" style="margin-left:auto;">📊 Excelga eksport</button>
    </div>
    <div class="toolbar">
      <button class="btn ${bhHolatFiltr === '' ? '' : 'ghost'}" data-bh-filtr=""
        style="${bhHolatFiltr === '' ? 'background:var(--navy);color:#fff;' : ''}">Barchasi: ${data.royxat.length}</button>
      ${kartalar}
    </div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th>Anketa №</th><th>PINFL/STIR</th><th>Mijoz</th><th>Turi</th>
            <th>Davo summasi</th><th>Ariza sanasi</th><th>Portal holati</th>
            <th>Murojaat №</th><th>Ijro muddati</th><th>Ilovalar</th><th></th>
          </tr></thead>
          <tbody>
            ${royxat.map(r => `<tr>
              <td>${r.anketa_raqami}</td><td>${r.pinfl_stir}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.turi}</td>
              <td>${formatSum(r.davo_summasi)}</td><td>${r.davo_ariza_sana}</td>
              <td style="font-weight:600;">${r.holat_nomi}</td>
              <td>${r.murojaat_raqami || '—'}</td><td>${r.ijro_muddati || '—'}</td>
              <td>${r.ilovalar_soni > 0 ? `📎 ${r.ilovalar_soni} ta` : '—'}</td>
              <td><button class="btn-gold" data-bh-anketa="${r.anketa_raqami}"
                style="padding:4px 10px; font-size:11.5px; margin-left:0;">📋 Portal ma'lumotlari</button></td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
    ${royxat.length === 0 ? '<div class="page-sub" style="margin-top:12px;">Bu holatda ish topilmadi.</div>' : ''}
  `;

  body.querySelectorAll('[data-bh-filtr]').forEach(btn => {
    btn.addEventListener('click', () => { bhHolatFiltr = btn.dataset.bhFiltr; bhRoyxatniChizish(); });
  });
  const qidirBajar = () => {
    bhQidiruv = document.getElementById('bh-qidiruv').value.trim();
    bhRoyxatniChizish();
  };
  document.getElementById('bh-qidir').addEventListener('click', qidirBajar);
  document.getElementById('bh-qidiruv').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') qidirBajar();
  });
  const tozalaBtn = document.getElementById('bh-qidiruv-tozalash');
  if (tozalaBtn) tozalaBtn.addEventListener('click', () => { bhQidiruv = ''; bhRoyxatniChizish(); });
  document.getElementById('bh-excel').addEventListener('click', () => {
    tayyorJildYuklabOlish(`${API_BASE}/bh/excel`);
  });
  body.querySelectorAll('[data-bh-anketa]').forEach(btn => {
    btn.addEventListener('click', () => bhPortalDialogOchish(btn.dataset.bhAnketa));
  });
}

function bhPortalDialogOchish(anketa) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `<div style="background:#fff;border-radius:12px;padding:20px 24px;width:780px;max-height:88vh;overflow-y:auto;" id="bh-modal"><div class="loading">Yuklanmoqda...</div></div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', async (e) => {
    if (e.target === overlay) { overlay.remove(); await bhRoyxatniChizish(); }
  });
  bhPortalModalniChizish(anketa, overlay);
}

const BH_BOLIM_NOMLARI = {
  yuborilgan_bolim: '📍 Yuborilgan bo\'lim',
  davogar: '🏦 Da\'vogar (bank)',
  javobgar: '👤 Javobgar',
  kredit_taminoti: '🔒 Kredit ta\'minoti',
  kredit_shartnoma: '📑 Kredit shartnoma',
  qarz: '💰 Qarz',
};

async function bhPortalModalniChizish(anketa, overlay) {
  const content = overlay.querySelector('#bh-modal');
  const d = await apiGet(`/bh/malumot?anketa=${encodeURIComponent(anketa)}`);
  if (d.xato) { content.innerHTML = `<div class="page-sub" style="color:var(--err);">${d.xato}</div>`; return; }
  const m = d.murojaat || {};
  const joriyHolat = m.holati || 'tayyorlanmoqda';

  // Portal bo'limlarini, har bir maydonni NUSXALASH tugmasi bilan chizamiz.
  const tahrirlanadigan = d.tahrir_maydonlari || {};
  const bolimlarHtml = Object.entries(d.malumotlar).map(([bolim, maydonlar]) => `
    <div class="card" style="margin-bottom:10px;">
      <div class="card-h">${BH_BOLIM_NOMLARI[bolim] || bolim}</div>
      <table style="width:100%; font-size:12.5px;">
        ${Object.entries(maydonlar).map(([k, v]) => {
          const maydon = tahrirlanadigan[k];
          const bosh = v === '' || v === null;
          // Xodim qo'lda tuzatgan bo'lsa, buni belgilab qo'yamiz.
          const qoldaOzgartirilgan = maydon && m[maydon] !== undefined
            && m[maydon] !== null && m[maydon] !== '';
          return `<tr>
          <td style="width:42%; color:var(--muted); padding:4px 0;">${k}</td>
          <td style="font-weight:600;" data-bh-qiymat="${maydon || ''}">
            ${bosh ? '<span style="color:var(--muted);font-weight:400;">—</span>' : v}
            ${qoldaOzgartirilgan ? ' <span style="font-size:10px;color:var(--muted);font-weight:400;">(qo\'lda)</span>' : ''}
          </td>
          <td style="width:130px; text-align:right; white-space:nowrap;">
            ${bosh ? '' : `<button class="btn" data-bh-nusxa="${String(v).replace(/"/g, '&quot;')}"
              style="padding:2px 8px; font-size:11px;">📋</button>`}
            ${maydon ? `<button class="btn" data-bh-tahrir="${maydon}" data-bh-nomi="${k.replace(/"/g, '&quot;')}"
              data-bh-joriy="${String(bosh ? '' : v).replace(/"/g, '&quot;')}"
              style="padding:2px 8px; font-size:11px;">✏</button>` : ''}
          </td>
        </tr>`;
        }).join('')}
      </table>
    </div>
  `).join('');

  content.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
      <div style="font-size:16px; font-weight:700;">🌐 Portal ma'lumotlari — ${anketa}</div>
      <button class="btn" id="bh-yopish">✕</button>
    </div>
    <div class="page-sub" style="margin-bottom:12px;">
      Quyidagi qiymatlar portfeldan avtomatik tayyorlandi — biznes-hamroh.uz shakliga nusxalab qo'ying.
      Holati: <b>${d.holat_nomlari[joriyHolat] || joriyHolat}</b>
    </div>

    <div class="btn-row" style="margin-bottom:12px;">
      <button class="btn-gold" id="bh-hammasi-nusxa" style="margin-left:0;">📋 Hammasini nusxalash</button>
    </div>

    ${bolimlarHtml}

    <div class="card" style="margin-bottom:10px;">
      <div class="card-h">📎 Ilovalar (portalga yuklanadigan hujjatlar)</div>
      ${d.ilovalar.length > 0 ? `
        <table style="width:100%; font-size:12.5px; margin-bottom:8px;">
          ${d.ilovalar.map(il => `<tr>
            <td style="padding:4px 0;">${il.ilova_turi}</td>
            <td style="width:90px;"><a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(il.fayl_yoli)}" target="_blank">👁 Ko'rish</a></td>
            <td style="width:50px;"><button class="btn danger" data-bh-ilova="${il.id}" style="padding:2px 8px; font-size:11px;">🗑</button></td>
          </tr>`).join('')}
        </table>` : '<div class="page-sub">Hali ilova biriktirilmagan.</div>'}
      <div class="btn-row" style="margin-top:8px;">
        <select class="tb-select" id="bh-ilova-turi" style="width:340px;">
          <option value="">— Ilova turini tanlang —</option>
          ${d.ilova_turlari.map(t => `<option value="${t}">${t}</option>`).join('')}
        </select>
        <input type="file" id="bh-ilova-file" style="width:180px;">
        <button class="btn-gold" id="bh-ilova-qoshish" style="margin-left:0;">📤 Qo'shish</button>
      </div>
    </div>

    <div class="card">
      <div class="card-h">📤 Portal holati</div>
      <div class="btn-row" style="margin-bottom:8px;">
        <input class="tb-input" id="bh-murojaat-raqam" placeholder="Murojaat № (193/006526-ARZ)"
          style="width:210px;" value="${m.murojaat_raqami || ''}">
        <input class="tb-input" id="bh-yub-sana" placeholder="Yuborilgan sana"
          style="width:140px;" value="${m.yuborilgan_sana || ''}">
        <input class="tb-input" id="bh-ijro-muddat" placeholder="Ijro muddati"
          style="width:140px;" value="${m.ijro_muddati || ''}">
      </div>
      <div class="btn-row" style="margin-bottom:10px;">
        <button class="btn-gold" data-bh-holat="yuborildi" style="margin-left:0;">📤 Portalga yuborildi</button>
        <button class="btn" data-bh-holat="javob_kutilmoqda">⏳ Javob kutilmoqda</button>
        <button class="btn danger" data-bh-holat="rad_etildi">✕ Rad etildi</button>
      </div>
      <div style="background:#F4F6FB; border-radius:8px; padding:10px 12px;">
        <div style="font-size:12.5px; font-weight:600; margin-bottom:6px;">
          ✓ Qabul qilindi (maqullangan) — tasdiqlovchi hujjat MAJBURIY
        </div>
        ${m.tasdiq_fayl ? `<div style="font-size:12px; margin-bottom:6px;">
          ✓ Tasdiq hujjati yuklangan &nbsp;
          <a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(m.tasdiq_fayl)}" target="_blank">👁 Ko'rish</a>
        </div>` : ''}
        <div class="btn-row">
          <input type="file" id="bh-tasdiq-file" accept=".pdf" style="width:220px;">
          <button class="btn" data-bh-holat="qabul_qilindi"
            style="background:#1E6B2E;color:#fff; margin-left:0;">✓ Qabul qilindi</button>
        </div>
      </div>
      <label style="display:block; margin-top:8px; font-size:12.5px;">Izoh (rad etilsa sababi)<br>
        <textarea class="tb-input" id="bh-izoh" style="width:100%;" rows="2">${m.natija_izoh || ''}</textarea></label>
    </div>
  `;

  content.querySelector('#bh-yopish').addEventListener('click', async () => {
    overlay.remove();
    await bhRoyxatniChizish();
  });

  // Bitta maydonni nusxalash
  content.querySelectorAll('[data-bh-nusxa]').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.bhNusxa);
        const eski = btn.textContent;
        btn.textContent = '✓ Olindi';
        setTimeout(() => { btn.textContent = eski; }, 1200);
      } catch (e) { alert('Nusxalashda xato: ' + e.message); }
    });
  });

  // Maydonni qo'lda o'zgartirish (portal boshqacha qiymat talab qilsa)
  content.querySelectorAll('[data-bh-tahrir]').forEach(btn => {
    btn.addEventListener('click', async () => {
      // MUHIM: brauzerning `prompt()` oynasi Electronda ishlamaydi —
      // shuning uchun dasturning o'z dialogi ishlatiladi.
      const yangi = await matnSorash(btn.dataset.bhNomi,
        btn.dataset.bhJoriy, "Portal talab qilgan qiymatni yozing.");
      if (yangi === null) return;
      const res = await fetch(`${API_BASE}/bh/saqlash`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anketa_raqami: anketa, [btn.dataset.bhTahrir]: yangi.trim() }),
      });
      const dd = await res.json();
      if (dd.xato) { alert('Xato: ' + dd.xato); return; }
      await bhPortalModalniChizish(anketa, overlay);
    });
  });

  // Barcha maydonlarni bir yo'la nusxalash
  content.querySelector('#bh-hammasi-nusxa').addEventListener('click', async () => {
    const qatorlar = [];
    for (const [bolim, maydonlar] of Object.entries(d.malumotlar)) {
      qatorlar.push(`── ${BH_BOLIM_NOMLARI[bolim] || bolim} ──`);
      for (const [k, v] of Object.entries(maydonlar)) qatorlar.push(`${k}: ${v}`);
      qatorlar.push('');
    }
    try {
      await navigator.clipboard.writeText(qatorlar.join('\n'));
      alert("Barcha portal ma'lumotlari nusxalandi.");
    } catch (e) { alert('Nusxalashda xato: ' + e.message); }
  });

  content.querySelector('#bh-ilova-qoshish').addEventListener('click', async () => {
    const turi = content.querySelector('#bh-ilova-turi').value;
    const f = content.querySelector('#bh-ilova-file').files[0];
    if (!turi || !f) { alert('Ilova turini tanlang va faylni biriktiring.'); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('ilova_turi', turi);
    fd.append('file', f);
    const res = await fetch(`${API_BASE}/bh/ilova_yuklash`, { method: 'POST', body: fd });
    const dd = await res.json();
    if (dd.xato) { alert('Xato: ' + dd.xato); return; }
    await bhPortalModalniChizish(anketa, overlay);
  });

  content.querySelectorAll('[data-bh-ilova]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm("Bu ilovani o'chirasizmi?")) return;
      await fetch(`${API_BASE}/bh/ilova/${btn.dataset.bhIlova}`, { method: 'DELETE' });
      await bhPortalModalniChizish(anketa, overlay);
    });
  });

  content.querySelectorAll('[data-bh-holat]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const holat = btn.dataset.bhHolat;
      // MUHIM: "Qabul qilindi" holati ishni Sud bosqichiga o'tkazadi,
      // shuning uchun uni tasdiqlovchi PDF hujjat MAJBURIY.
      const fd = new FormData();
      fd.append('anketa_raqami', anketa);
      fd.append('holati', holat);
      fd.append('murojaat_raqami', content.querySelector('#bh-murojaat-raqam').value.trim());
      fd.append('yuborilgan_sana', content.querySelector('#bh-yub-sana').value.trim());
      fd.append('ijro_muddati', content.querySelector('#bh-ijro-muddat').value.trim());
      fd.append('izoh', content.querySelector('#bh-izoh').value.trim());
      if (holat === 'qabul_qilindi') {
        const tf = content.querySelector('#bh-tasdiq-file').files[0];
        if (!tf && !m.tasdiq_fayl) {
          alert("Maqullanganini tasdiqlovchi hujjat (PDF) yuklash MAJBURIY.");
          return;
        }
        if (tf) fd.append('tasdiq_fayl', tf);
      }
      const res = await fetch(`${API_BASE}/bh/holat`, { method: 'POST', body: fd });
      const dd = await res.json();
      if (dd.xato) { alert('Xato: ' + dd.xato); return; }
      if (dd.sudga_otdi || (dd.jild && dd.jild.qoshilgan_soni !== undefined)) {
        const j = dd.jild || {};
        let xabar = "Murojaat qabul qilindi.\n\n";
        if (dd.sudga_otdi) {
          xabar += "• Ish \"SUD Ishlari → SSPdan o'tib sudga jo'natiladiganlar\" ro'yxatiga o'tkazildi.\n";
        }
        if (j.qoshilgan_soni !== undefined) {
          xabar += `• Sud yig'ma jildi avtomatik shakllantirildi: Titul + ${j.qoshilgan_soni} ta hujjat qo'shildi.`;
        }
        alert(xabar);
      }
      await bhPortalModalniChizish(anketa, overlay);
    });
  });
}

// ═══ SUG'URTADAN UNDIRISH ═════════════════════════════════════════════
// Bo'limning asosiy mantig'i: MIB (Majburiy ijro byurosi) CHIQARGAN
// hujjat — "undirib bo'lmaganligi to'g'risidagi dalolatnoma" yoki "ijro
// hujjatini qaytarish to'g'risidagi qaror" kabi — sug'urta kompaniyasidan
// qarzni undirish uchun ASOS bo'ladi. Ro'yxatga MIBga o'tkazilgan
// BARCHA ishlar tushadi. Jarayon 3 bosqich:
//     Ariza yuborildi  →  To'landi  |  Rad etildi
