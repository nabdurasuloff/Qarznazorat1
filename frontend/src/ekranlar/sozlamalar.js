// Sozlamalar ekrani (shablonlar, zaxira, foydalanuvchilar).
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

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
    biznes_hamroh: { nomi: 'Biznes-hamroh.uz', fields: BH_SOZLAMA_FIELDS },
    sud: { nomi: 'Sud Ishlari', fields: [] },
    mib: { nomi: 'MIB', fields: MIB_SOZLAMA_FIELDS },
    sugurta_undirish: { nomi: "Sug'urtadan undirish", fields: SUGURTA_UNDIRISH_SOZLAMA_FIELDS },
    vafot: { nomi: 'Vafot etganlar', fields: VAFOT_SOZLAMA_FIELDS },
    umumiy: { nomi: "Hujjatlar joyi va xavfsizlik", fields: UMUMIY_SOZLAMA_FIELDS },
    zaxira: { nomi: "🛟 Zaxira nusxalar", fields: [] },
    foydalanuvchilar: { nomi: "Foydalanuvchilar (tarmoq)", fields: [] },
  };

  async function chizish() {
    main.innerHTML = `
      <div class="page-title">Sozlamalar</div>
      <div style="display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap;">
        ${Object.entries(bolimlar).map(([k, v]) => `
          <button class="btn" data-bolim="${k}" style="${k === joriyBolim ? 'background:var(--navy);color:#fff;' : ''}">${xavfsizMatn(v.nomi)}</button>
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
    if (joriyBolim === 'zaxira') {
      await zaxiraBolimiChizish(container);
      return;
    }
    if (joriyBolim === 'umumiy') qoshimcha = xavfsizlikBolimiHtml();
    else if (joriyBolim === 'talabnoma') qoshimcha = shablonBolimiHtml(
      "Xat shabloni (Word)", "Yangi shablon yuklasangiz, hali yuborilmagan ('Tayyor' holatidagi) xatlar avtomatik shu yangi shablon bilan qayta tayyorlanadi.", 'xat');
    else if (joriyBolim === 'vafot') qoshimcha = shablonBolimiHtml(
      "Sug'urta xabarnomasi shabloni (Word)", "Vafot etgan mijozlar bo'yicha sug'urta kompaniyasiga yuboriladigan xabarnoma shabloni.", 'sugurta');
    else if (joriyBolim === 'mib') qoshimcha = shablonBolimiHtml(
      "Yig'ma jild tituli shabloni (Word)", "MIBga o'tkazish tasdiqlanganda avtomatik yaratiladigan yig'ma jild muqova hujjati shabloni.", 'yigma_jild');
    else if (joriyBolim === 'sugurta_undirish') {
      qoshimcha = shablonBolimiHtml(
        "Sug'urta tovoni arizasi shabloni — MIB qarori bo'yicha (Word)",
        "Kredit qarzini muddatidan oldin undirish bo'yicha sud qarori asosida sug'urta kompaniyasiga yuboriladigan ariza shabloni. Tizim uni mijoz, kredit shartnomasi, sud qarori va polis ma'lumotlari bilan to'ldiradi.",
        'sugurta_tovon');
      qoshimcha += shablonBolimiHtml(
        "Sug'urta tovoni arizasi shabloni — vafot bo'yicha (Word)",
        "Sug'urtalangan shaxsning vafoti munosabati bilan sug'urta tovonini to'lash to'g'risidagi ariza shabloni. Tizim uni vafot sanasi, guvohnoma, pasport va qarzdorlik ma'lumotlari bilan to'ldiradi.",
        'vafot_sugurta_tovon');
    }
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
      qoshimcha += shablonBolimiHtml(
        "MA'LUMOTNOMA — kredit qarzdorligi holati to'g'risida (Word)",
        "Sudga da'vo arizasi bilan birga beriladigan rasmiy ma'lumotnoma. Tizim uni shartnoma ma'lumotlari, berilgan kredit, qaytarilgan va qoldiq qarz, foiz, penya bilan avtomatik to'ldiradi.",
        'sud_malumotnoma_qarzdorlik');
      qoshimcha += shablonBolimiHtml(
        "QO'SHIMCHA MA'LUMOTNOMA — qarzdorlik o'zgarishi to'g'risida (Word)",
        "Ish sudda ko'rilayotganda qarz o'zgarsa (to'lov tushsa yoki foiz o'ssa) beriladigan ma'lumotnoma. Tizim avvalgi (da'vodagi) va bugungi summani solishtirib, farqni va tushgan to'lovlarni jadvalga chiqaradi.",
        'sud_qoshimcha_malumotnoma');
    }
    await sozlamalarEkraniniQurish(container, `${b.nomi} sozlamalari`, b.fields, qoshimcha);
    if (joriyBolim === 'umumiy') xavfsizlikBolimiIshga(container);
    else if (['talabnoma', 'vafot', 'mib'].includes(joriyBolim)) shablonBolimiIshga(container, { talabnoma: 'xat', vafot: 'sugurta', mib: 'yigma_jild' }[joriyBolim]);
    else if (joriyBolim === 'davo') { shablonBolimiIshga(container, 'davo'); shablonBolimiIshga(container, 'reestr_ssp'); }
    else if (joriyBolim === 'sud') {
      shablonBolimiIshga(container, 'sud_yigma_jild');
      shablonBolimiIshga(container, 'malumotnoma_topshirishda');
      shablonBolimiIshga(container, 'malumotnoma_kun');
      shablonBolimiIshga(container, 'sud_malumotnoma_qarzdorlik');
      shablonBolimiIshga(container, 'sud_qoshimcha_malumotnoma');
    }
    if (joriyBolim === 'mib') {
      await mibHarakatTurlariBolimiChizish(container);
    }
    if (joriyBolim === 'sugurta_undirish') {
      shablonBolimiIshga(container, 'sugurta_tovon');
      shablonBolimiIshga(container, 'vafot_sugurta_tovon');
      await sugurtaKompaniyalarBolimiChizish(container);
    }
  }
  await chizish();
}

// ═══ ZAXIRA NUSXALAR ══════════════════════════════════════════════════
// Butun huquqiy ish bitta baza faylida saqlanadi. Shu sabab tizim har
// kuni avtomatik zaxira nusxa oladi; bu yerda ularni ko'rish, qo'lda
// nusxa olish, yuklab olish va kerak bo'lsa tiklash mumkin.

// ═══ ZAXIRA NUSXALAR ══════════════════════════════════════════════════
// Butun huquqiy ish bitta baza faylida saqlanadi. Shu sabab tizim har
// kuni avtomatik zaxira nusxa oladi; bu yerda ularni ko'rish, qo'lda
// nusxa olish, yuklab olish va kerak bo'lsa tiklash mumkin.
async function zaxiraBolimiChizish(container) {
  const hajm = (b) => b > 1048576 ? (b / 1048576).toFixed(1) + ' MB' : Math.round(b / 1024) + ' KB';
  const chizish = async () => {
    const d = await apiGet('/zaxira/royxat');
    container.innerHTML = `
      <div class="card" style="margin-bottom:16px;">
        <div class="card-h">🛟 Zaxira nusxalar</div>
        <div class="page-sub">
          Butun ish (mijozlar, xatlar, sud va MIB jarayonlari, sug'urta ishlari) bitta baza faylida
          saqlanadi. Tizim <b>har kuni dastur ishga tushganda avtomatik</b> zaxira nusxa oladi va
          oxirgi ${d.saqlash_kun} kunlik nusxalarni saqlaydi.
        </div>
        <div style="background:${d.bugun_olinganmi ? '#EAF5EC' : '#FDF3E7'}; border-radius:8px; padding:10px 12px; margin:10px 0; font-size:12.5px;">
          ${d.bugun_olinganmi
            ? "✓ Bugungi zaxira nusxa olingan."
            : "⚠ Bugun hali zaxira olinmagan — quyidagi tugma bilan darhol olishingiz mumkin."}
          <br><span style="color:var(--muted);">Saqlanadigan joy: ${d.papka}</span>
        </div>
        <div class="btn-row">
          <button class="btn-gold" id="zx-yaratish" style="margin-left:0;">💾 Hozir zaxira nusxa olish</button>
        </div>
      </div>

      <div class="card">
        <div class="card-h">Mavjud nusxalar (${d.royxat.length} ta)</div>
        ${d.royxat.length === 0 ? '<div class="page-sub">Hali nusxa olinmagan.</div>' : `
        <div class="table-wrap"><div class="table-scroll" style="max-height:400px;">
          <table>
            <thead><tr><th>Sana va vaqt</th><th>Hajmi</th><th>Fayl nomi</th><th></th></tr></thead>
            <tbody>
              ${d.royxat.map((z, i) => `<tr>
                <td style="white-space:nowrap;">${z.sana}${i === 0 ? ' <span style="color:#1E6B2E;font-size:11px;">(eng yangi)</span>' : ''}</td>
                <td style="white-space:nowrap;">${hajm(z.hajmi)}</td>
                <td style="font-size:11.5px; color:var(--muted);">${z.nomi}</td>
                <td style="white-space:nowrap; text-align:right;">
                  <a class="btn" href="${API_BASE}/zaxira/yuklab_olish?yoli=${encodeURIComponent(z.yoli)}"
                     style="padding:2px 8px; font-size:11px; text-decoration:none;">⬇ Yuklab olish</a>
                  <button class="btn" data-zx-tiklash="${z.yoli.replace(/"/g, '&quot;')}"
                     data-zx-sana="${z.sana}" style="padding:2px 8px; font-size:11px;">↩ Tiklash</button>
                  <button class="btn danger" data-zx-ochirish="${z.yoli.replace(/"/g, '&quot;')}"
                     style="padding:2px 8px; font-size:11px;">🗑</button>
                </td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div></div>`}
      </div>
    `;

    container.querySelector('#zx-yaratish').addEventListener('click', async (e) => {
      const btn = e.target; const eski = btn.textContent;
      btn.textContent = 'Olinmoqda...'; btn.disabled = true;
      try {
        const r = await fetch(`${API_BASE}/zaxira/yaratish`, { method: 'POST' });
        const dd = await r.json();
        if (dd.xato) { alert('Xato: ' + dd.xato); return; }
        alert('Zaxira nusxa olindi:\n' + dd.nomi);
        await chizish();
      } finally { btn.textContent = eski; btn.disabled = false; }
    });

    container.querySelectorAll('[data-zx-tiklash]').forEach(btn => {
      btn.addEventListener('click', async () => {
        // MUHIM: tiklash joriy ma'lumotlarni almashtiradi — ikki bosqichli tasdiq.
        if (!confirm(`DIQQAT!\n\n${btn.dataset.zxSana} holatiga qaytariladi.\n\n`
          + `Shu sanadan KEYIN kiritilgan barcha ma'lumotlar (yangi xatlar, sud va MIB `
          + `harakatlari, sug'urta ishlari) YO'QOLADI.\n\nDavom etasizmi?`)) return;
        if (!confirm("Ishonchingiz komilmi? Bu amalni ortga qaytarib bo'lmaydi.\n\n"
          + "(Ehtiyot uchun joriy holat ham alohida nusxalab qo'yiladi.)")) return;
        const r = await fetch(`${API_BASE}/zaxira/tiklash`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ yoli: btn.dataset.zxTiklash }),
        });
        const dd = await r.json();
        if (dd.xato) { alert('Xato: ' + dd.xato); return; }
        alert("Baza tiklandi. Dasturni qayta ishga tushiring.");
        await chizish();
      });
    });

    container.querySelectorAll('[data-zx-ochirish]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm("Bu zaxira nusxani o'chirasizmi?")) return;
        await fetch(`${API_BASE}/zaxira/ochirish`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ yoli: btn.dataset.zxOchirish }),
        });
        await chizish();
      });
    });
  };
  await chizish();
}
