// Sug'urtadan undirish ekrani (MIB qarori va vafot bo'yicha).
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

// ═══ SUG'URTADAN UNDIRISH ═════════════════════════════════════════════
// Bo'limning asosiy mantig'i: MIB (Majburiy ijro byurosi) CHIQARGAN
// hujjat — "undirib bo'lmaganligi to'g'risidagi dalolatnoma" yoki "ijro
// hujjatini qaytarish to'g'risidagi qaror" kabi — sug'urta kompaniyasidan
// qarzni undirish uchun ASOS bo'ladi. Ro'yxatga MIBga o'tkazilgan
// BARCHA ishlar tushadi. Jarayon 3 bosqich:
//     Ariza yuborildi  →  To'landi  |  Rad etildi

let sugurtaHolatFiltr = '';

let sugurtaQidiruv = '';

let sugurtaTab = 'mib';   // 'mib' | 'vafot'

async function sugurtaUndirishniYuklash(main) {
  main.innerHTML = `
    <div class="page-title">Sug'urtadan undirish</div>
    <div class="page-sub" id="sug-tavsif"></div>
    <div style="display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap;">
      <button class="btn ${sugurtaTab === 'mib' ? '' : 'ghost'}" data-sug-tab="mib"
        style="${sugurtaTab === 'mib' ? 'background:var(--navy);color:#fff;' : ''}">🏛 MIB qarorlari asosida</button>
      <button class="btn ${sugurtaTab === 'vafot' ? '' : 'ghost'}" data-sug-tab="vafot"
        style="${sugurtaTab === 'vafot' ? 'background:var(--navy);color:#fff;' : ''}">🕊 Vafot etganlar</button>
    </div>
    <div id="sug-body"><div class="loading">Yuklanmoqda...</div></div>
  `;
  main.querySelectorAll('[data-sug-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      sugurtaTab = btn.dataset.sugTab;
      sugurtaHolatFiltr = ''; sugurtaQidiruv = '';
      sugurtaUndirishniYuklash(main);
    });
  });
  document.getElementById('sug-tavsif').innerHTML = sugurtaTab === 'vafot'
    ? `Vafot etgan mijozlar bo'yicha sug'urta tovonini undirish. "Vafot etganlar" bo'limidagi
       <b>barcha mijozlar</b> shu yerda avtomatik ko'rinadi — sug'urtalangan shaxsning vafoti
       o'z-o'zidan sug'urta hodisasi hisoblanadi.`
    : `MIB chiqargan hujjat (dalolatnoma / qaror) asosida sug'urta kompaniyasidan qarzni undirish.
       <b>Diqqat:</b> bu yo'nalish faqat kredit qarzini <b>muddatidan oldin undirish</b> uchun
       chiqarilgan sud qarorlari bo'yicha hisoblanadi.`;
  if (sugurtaTab === 'vafot') await sugurtaVafotRoyxatniChizish();
  else await sugurtaRoyxatniChizish();
}

async function sugurtaVafotRoyxatniChizish() {
  const body = document.getElementById('sug-body');
  const data = await apiGet('/sugurta_undirish/vafot_royxat');

  let royxat = data.royxat;
  if (sugurtaHolatFiltr) royxat = royxat.filter(r => r.holati === sugurtaHolatFiltr);
  if (sugurtaQidiruv) {
    const q = sugurtaQidiruv.toLowerCase();
    royxat = royxat.filter(r => String(r.anketa_raqami).toLowerCase().includes(q)
      || String(r.mijoz_nomi).toLowerCase().includes(q));
  }

  const HOLAT_TARTIBI = ['tayyorlanmoqda', 'yuborildi', 'tolandi', 'rad_etildi'];
  const kartalar = HOLAT_TARTIBI.filter(k => data.holat_nomlari[k]).map(kod => {
    const soni = data.soni[kod] || 0;
    const faol = sugurtaHolatFiltr === kod;
    return `<button class="btn ${faol ? '' : 'ghost'}" data-sug-filtr="${kod}"
      style="${faol ? 'background:var(--navy);color:#fff;' : ''}">${data.holat_nomlari[kod]}: ${soni}</button>`;
  }).join('');
  const jamiTolangan = data.royxat.reduce((s, r) => s + (r.tolangan_summa || 0), 0);
  const polisNomi = { tekshirilmagan: '❔ Tekshirilmagan', amalda: '✓ Amalda', muddati_otgan: "✕ Muddati o'tgan" };

  body.innerHTML = `
    <div class="toolbar">
      <input class="tb-input" id="sug-qidiruv" placeholder="Anketa raqami yoki mijoz nomi"
        style="width:250px;" value="${sugurtaQidiruv}">
      <button class="btn" id="sug-qidir">🔍 Topish</button>
      ${sugurtaQidiruv ? '<button class="btn ghost" id="sug-qidiruv-tozalash">✕ Tozalash</button>' : ''}
      <button class="btn-gold" id="sug-excel" style="margin-left:auto;">📊 Excelga eksport</button>
    </div>
    <div class="toolbar">
      <button class="btn ${sugurtaHolatFiltr === '' ? '' : 'ghost'}" data-sug-filtr=""
        style="${sugurtaHolatFiltr === '' ? 'background:var(--navy);color:#fff;' : ''}">Barchasi: ${data.royxat.length}</button>
      ${kartalar}
      ${jamiTolangan > 0 ? `<div style="margin-left:auto; font-weight:700; color:#1E6B2E;">
        Sug'urtadan undirilgan: ${formatSum(jamiTolangan)} so'm</div>` : ''}
    </div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th>Anketa №</th><th>Mijoz</th><th>Vafot sanasi</th><th>Polis holati</th>
            <th>Jami qarz</th><th>Sug'urta kompaniyasi</th><th>Ariza</th>
            <th>Holati</th><th>Talab / To'langan</th><th></th>
          </tr></thead>
          <tbody>
            ${royxat.map(r => `<tr>
              <td>${r.anketa_raqami}</td>
              <td style="max-width:180px;"><div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${String(r.mijoz_nomi).replace(/"/g, '&quot;')}">${xavfsizMatn(r.mijoz_nomi)}</div>
                <span style="font-size:11px;color:var(--muted);">${r.pinfl_stir}</span></td>
              <td style="white-space:nowrap;">${r.vafot_sanasi || '—'}</td>
              <td style="white-space:nowrap;">${polisNomi[r.polis_holati] || r.polis_holati}</td>
              <td style="white-space:nowrap;">${formatSum(r.jami_qarz)}</td>
              <td style="max-width:150px;"><div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${r.sugurta_kompaniya || '—'}</div>
                ${r.polis_raqami ? `<span style="font-size:11px;color:var(--muted);">${r.polis_raqami}</span>` : ''}</td>
              <td style="white-space:nowrap;">${r.ariza_bor ? `📄 ${r.ariza_raqami || 'tayyor'}` : '<span style="color:var(--muted);">—</span>'}</td>
              <td style="font-weight:600; white-space:nowrap;">${r.holat_nomi}
                ${r.kechikkan ? `<br><span style="font-size:11px;color:var(--err);">⚠ ${r.kutilgan_kun} kun javob yo'q</span>` : ''}</td>
              <td>${r.talab_summasi ? formatSum(r.talab_summasi) : '—'}
                ${r.tolangan_summa ? `<br><span style="color:#1E6B2E;font-weight:600;">✓ ${formatSum(r.tolangan_summa)}</span>` : ''}</td>
              <td style="white-space:nowrap;"><button class="btn-gold" data-sug-vafot="${r.anketa_raqami}"
                style="padding:4px 10px; font-size:11.5px; margin-left:0;">🕊 Ochish</button></td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
    ${royxat.length === 0 ? `<div class="page-sub" style="margin-top:12px;">
      ${data.royxat.length === 0
        ? "\"Vafot etganlar\" bo'limida hali mijoz kiritilmagan — u yerga mijoz qo'shilsa, bu yerda avtomatik ko'rinadi."
        : 'Bu holatda ish topilmadi.'}</div>` : ''}
  `;

  body.querySelectorAll('[data-sug-filtr]').forEach(btn => {
    btn.addEventListener('click', () => { sugurtaHolatFiltr = btn.dataset.sugFiltr; sugurtaVafotRoyxatniChizish(); });
  });
  const qidirBajar = () => {
    sugurtaQidiruv = document.getElementById('sug-qidiruv').value.trim();
    sugurtaVafotRoyxatniChizish();
  };
  document.getElementById('sug-qidir').addEventListener('click', qidirBajar);
  document.getElementById('sug-qidiruv').addEventListener('keydown', (e) => { if (e.key === 'Enter') qidirBajar(); });
  const tozalaBtn = document.getElementById('sug-qidiruv-tozalash');
  if (tozalaBtn) tozalaBtn.addEventListener('click', () => { sugurtaQidiruv = ''; sugurtaVafotRoyxatniChizish(); });
  document.getElementById('sug-excel').addEventListener('click', () => {
    tayyorJildYuklabOlish(`${API_BASE}/sugurta_undirish/vafot_excel`);
  });
  body.querySelectorAll('[data-sug-vafot]').forEach(btn => {
    btn.addEventListener('click', () => sugurtaVafotDialogOchish(btn.dataset.sugVafot));
  });
}

function sugurtaVafotDialogOchish(anketa) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `<div style="background:#fff;border-radius:12px;padding:20px 24px;width:820px;max-height:88vh;overflow-y:auto;" id="sug-modal"><div class="loading">Yuklanmoqda...</div></div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', async (e) => {
    if (e.target === overlay) { overlay.remove(); await sugurtaVafotRoyxatniChizish(); }
  });
  sugurtaVafotModalniChizish(anketa, overlay);
}

async function sugurtaVafotModalniChizish(anketa, overlay) {
  const content = overlay.querySelector('#sug-modal');
  const d = await apiGet(`/sugurta_undirish/vafot_malumot?anketa=${encodeURIComponent(anketa)}`);
  if (d.xato) { content.innerHTML = `<div class="page-sub" style="color:var(--err);">${d.xato}</div>`; return; }
  const v = d.vafot;
  const u = d.undirish || {};
  const joriyHolat = u.holati || 'tayyorlanmoqda';
  const fayl = (yol) => `<a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(yol)}" target="_blank">👁 Ko'rish</a>`;
  const polisNomi = { tekshirilmagan: '❔ Tekshirilmagan', amalda: '✓ Amalda', muddati_otgan: "✕ Muddati o'tgan" };
  const q = (s) => String(s || '').replace(/"/g, '&quot;');

  content.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
      <div style="font-size:16px; font-weight:700;">🕊 Vafot bo'yicha sug'urta tovoni — ${xavfsizMatn(v.mijoz_nomi)}</div>
      <button class="btn" id="sug-yopish">✕</button>
    </div>
    <div class="page-sub" style="margin-bottom:12px;">
      Anketa ${anketa} · Holati: <b>${d.holat_nomlari[joriyHolat] || joriyHolat}</b>
    </div>

    <div class="card" style="margin-bottom:10px;">
      <div class="card-h">🕊 Vafot va kredit ma'lumotlari (tizimdan)</div>
      <table style="width:100%; font-size:12.5px;">
        <tr><td style="width:40%; color:var(--muted); padding:3px 0;">Vafot sanasi</td><td style="font-weight:600;">${v.vafot_sanasi || '—'}</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">PINFL / STIR</td><td style="font-weight:600;">${v.pinfl_stir || '—'}</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">Kredit shartnoma sanasi</td><td style="font-weight:600;">${v.shartnoma_sanasi || '—'}</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">Polis holati</td><td style="font-weight:600;">${polisNomi[v.polis_holati] || v.polis_holati}</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">Asosiy qarz</td><td style="font-weight:600;">${formatSum(v.asosiy_qarz)} so'm</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">Hisoblangan foizlar</td><td style="font-weight:600;">${formatSum(v.foiz_qarz)} so'm</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">Jami qarz</td><td style="font-weight:700; color:var(--err);">${formatSum(v.jami_qarz)} so'm</td></tr>
        ${v.olimlik_guvohnomasi_fayl ? `<tr><td style="color:var(--muted); padding:3px 0;">Vafot guvohnomasi</td><td>${fayl(v.olimlik_guvohnomasi_fayl)}</td></tr>` : ''}
        ${v.pasport_fayl ? `<tr><td style="color:var(--muted); padding:3px 0;">Pasport nusxasi</td><td>${fayl(v.pasport_fayl)}</td></tr>` : ''}
        ${v.sugurta_polis_fayl ? `<tr><td style="color:var(--muted); padding:3px 0;">Sug'urta polisi</td><td>${fayl(v.sugurta_polis_fayl)}</td></tr>` : ''}
      </table>
      ${!v.olimlik_guvohnomasi_fayl ? `<div style="margin-top:8px; font-size:12.5px; color:var(--err);">
        ⚠ Vafot guvohnomasi yuklanmagan — "Ariza yuborildi" deb belgilash uchun uni
        "Vafot etganlar" bo'limida yuklashingiz kerak.</div>` : ''}
    </div>

    <div class="card" style="margin-bottom:10px; border-left:3px solid var(--gold);">
      <div class="card-h">✍ Qo'lda kiritiladigan ma'lumotlar (tizimda yo'q)</div>
      <div class="page-sub" style="margin-bottom:8px;">
        Bu maydonlar arizaga o'z joyiga qo'yiladi. Guvohnoma va pasport ma'lumotlarini
        hujjatlardan ko'chiring.
      </div>
      <div class="btn-row" style="margin-bottom:8px; align-items:flex-end;">
        <label style="font-size:11.5px; color:var(--muted);">Pasport seriyasi<br>
          <input class="tb-input" id="sv-pas-seriya" placeholder="AA" style="width:90px;" value="${q(u.pasport_seriya)}"></label>
        <label style="font-size:11.5px; color:var(--muted);">Pasport raqami<br>
          <input class="tb-input" id="sv-pas-raqam" placeholder="1234567" style="width:130px;" value="${q(u.pasport_raqam)}"></label>
        <label style="font-size:11.5px; color:var(--muted);">FHDYo guvohnomasi №<br>
          <input class="tb-input" id="sv-guv-raqam" placeholder="123456" style="width:140px;" value="${q(u.guvohnoma_raqami)}"></label>
        <label style="font-size:11.5px; color:var(--muted);">Guvohnoma sanasi<br>
          <input class="tb-input" id="sv-guv-sana" placeholder="kk.oo.yyyy" style="width:130px;" value="${q(u.guvohnoma_sanasi)}"></label>
      </div>
      <div class="btn-row" style="margin-bottom:8px; align-items:flex-end;">
        <label style="font-size:11.5px; color:var(--muted); flex:1;">Vafot sababi<br>
          <input class="tb-input" id="sv-sabab" placeholder="masalan: yurak xuruji" style="width:100%;" value="${q(u.vafot_sababi)}"></label>
        <label style="font-size:11.5px; color:var(--muted);">Shartnoma bandi<br>
          <input class="tb-input" id="sv-band" placeholder="5.1" style="width:90px;" value="${q(u.shartnoma_bandi)}"></label>
      </div>
      <div class="btn-row" style="align-items:flex-end;">
        <label style="font-size:11.5px; color:var(--muted);">Sug'urta shartnomasi №<br>
          <input class="tb-input" id="sv-sh-raqam" placeholder="shartnoma raqami" style="width:170px;" value="${q(u.sugurta_shartnoma_raqami)}"></label>
        <label style="font-size:11.5px; color:var(--muted);">Shartnoma sanasi<br>
          <input class="tb-input" id="sv-sh-sana" placeholder="kk.oo.yyyy" style="width:130px;" value="${q(u.sugurta_shartnoma_sanasi)}"></label>
      </div>
    </div>

    <div class="card" style="margin-bottom:10px;">
      <div class="card-h">🛡 Sug'urta polisi va ariza</div>
      <div class="btn-row" style="margin-bottom:8px; align-items:flex-end;">
        <label style="font-size:11.5px; color:var(--muted);">Sug'urta kompaniyasi<br>
          <input class="tb-input" id="sv-kompaniya" list="sv-kompaniyalar" placeholder="kompaniya nomi"
            style="width:240px;" value="${q(u.sugurta_kompaniya || v.sugurta_kompaniya)}"></label>
        <datalist id="sv-kompaniyalar">${d.kompaniyalar.map(k => `<option value="${q(k)}">`).join('')}</datalist>
        <label style="font-size:11.5px; color:var(--muted);">Polis raqami<br>
          <input class="tb-input" id="sv-polis-raqam" placeholder="polis №" style="width:160px;"
            value="${q(u.polis_raqami || v.sugurta_polis_raqam)}"></label>
        <label style="font-size:11.5px; color:var(--muted);">Polis sanasi<br>
          <input class="tb-input" id="sv-polis-sana" placeholder="kk.oo.yyyy" style="width:130px;" value="${q(u.polis_sanasi)}"></label>
      </div>
      <div class="btn-row" style="margin-bottom:8px; align-items:flex-end;">
        <label style="font-size:11.5px; color:var(--muted);">Ariza raqami<br>
          <input class="tb-input" id="sv-ariza-raqam" placeholder="chiquvchi №" style="width:160px;" value="${q(u.ariza_raqami)}"></label>
        <label style="font-size:11.5px; color:var(--muted);">Ariza sanasi<br>
          <input class="tb-input" id="sv-ariza-sana" placeholder="kk.oo.yyyy" style="width:130px;" value="${q(u.ariza_sana)}"></label>
        <label style="font-size:11.5px; color:var(--muted);">Talab summasi<br>
          <input class="tb-input" id="sv-talab" placeholder="bo'sh qoldirsangiz — jami qarz" style="width:200px;" value="${u.talab_summasi || ''}"></label>
        <button class="btn" id="sv-saqlash" style="margin-left:0;">💾 Saqlash</button>
      </div>
      <div style="background:#F4F6FB; border-radius:8px; padding:10px 12px;">
        <div style="font-size:12.5px; font-weight:600; margin-bottom:6px;">
          📝 Arizani tizim o'zi tayyorlab beradi (shablon asosida)
        </div>
        <div class="page-sub" style="margin-bottom:8px;">
          "Sug'urtalangan shaxsning vafoti munosabati bilan sug'urta tovonini to'lash to'g'risida"gi
          ariza. Shablonni Sozlamalar → Sug'urtadan undirish bo'limida yangilashingiz mumkin.
        </div>
        <div class="btn-row">
          <select class="tb-select" id="sv-format" style="width:130px;">
            <option value="docx">Word (.docx)</option>
            <option value="pdf">PDF</option>
          </select>
          <button class="btn-gold" id="sv-ariza-yaratish" style="margin-left:0;">📝 Ariza tayyorlash</button>
          ${u.ariza_fayl ? `<span style="font-size:12.5px; margin-left:8px;">✓ Ariza tayyor ${fayl(u.ariza_fayl)}</span>` : ''}
        </div>
      </div>
    </div>

    <div class="card" style="margin-bottom:10px;">
      <div class="card-h">📎 Ilova hujjatlar</div>
      <div class="page-sub" style="margin-bottom:8px;">
        "Vafot etganlar" bo'limida yuklangan hujjatlar (guvohnoma, pasport, polis, kompaniya javobi)
        va kredit shartnomasi <b>avtomatik qo'shiladi</b>.
        ${d.avto_qoshildi > 0 ? `<br><span style="color:#1E6B2E;font-weight:600;">✓ Hozir ${d.avto_qoshildi} ta hujjat avtomatik qo'shildi.</span>` : ''}
      </div>
      ${d.hujjatlar.length > 0 ? `
        <table style="width:100%; font-size:12.5px; margin-bottom:8px;">
          ${d.hujjatlar.map(h => `<tr>
            <td style="padding:4px 0;">${xavfsizMatn(h.hujjat_nomi)}</td>
            <td style="width:90px;">${fayl(h.fayl_yoli)}</td>
            <td style="width:50px;"><button class="btn danger" data-sv-hujjat="${h.id}" style="padding:2px 8px; font-size:11px;">🗑</button></td>
          </tr>`).join('')}
        </table>` : '<div class="page-sub">Hali hujjat biriktirilmagan.</div>'}
      <div class="btn-row" style="margin-top:8px;">
        <input class="tb-input" id="sv-qosh-nomi" placeholder="Hujjat nomi (masalan: Tibbiy ma'lumotnoma №106)" style="width:340px;">
        <input type="file" id="sv-qosh-file" style="width:180px;">
        <button class="btn-gold" id="sv-qosh-yuklash" style="margin-left:0;">📤 Qo'shish</button>
      </div>
    </div>

    <div class="card">
      <div class="card-h">🔄 Holati</div>
      <div class="btn-row" style="margin-bottom:10px;">
        <button class="btn-gold" data-sv-holat="yuborildi" style="margin-left:0;">📤 Ariza yuborildi</button>
        <button class="btn" data-sv-holat="tolandi" style="background:#1E6B2E;color:#fff;">✓ To'landi</button>
        <button class="btn danger" data-sv-holat="rad_etildi">✕ Rad etildi</button>
      </div>
      <div class="btn-row" style="margin-bottom:8px; align-items:flex-end;">
        <label style="font-size:11.5px; color:var(--muted);">To'langan summa<br>
          <input class="tb-input" id="sv-tolangan" placeholder="masalan: 98000000" style="width:180px;" value="${u.tolangan_summa || ''}"></label>
        <label style="font-size:11.5px; color:var(--muted);">To'lov sanasi<br>
          <input class="tb-input" id="sv-tolov-sana" placeholder="kk.oo.yyyy" style="width:140px;" value="${q(u.tolov_sana)}"></label>
        <label style="font-size:11.5px; color:var(--muted);">Javob hujjati (ixtiyoriy)<br>
          <input type="file" id="sv-natija-file" style="width:200px;"></label>
      </div>
      <label style="display:block; font-size:12.5px;">Izoh (rad etilsa — sababi majburiy)<br>
        <textarea class="tb-input" id="sv-izoh" style="width:100%;" rows="2">${u.natija_izoh || ''}</textarea></label>
      ${u.natija_fayl ? `<div style="font-size:12.5px; margin-top:6px;">✓ Javob hujjati ${fayl(u.natija_fayl)}</div>` : ''}
    </div>
  `;

  content.querySelector('#sug-yopish').addEventListener('click', async () => {
    overlay.remove();
    await sugurtaVafotRoyxatniChizish();
  });

  const maydonlar = () => ({
    anketa_raqami: anketa, ish_turi: 'vafot',
    pasport_seriya: content.querySelector('#sv-pas-seriya').value.trim(),
    pasport_raqam: content.querySelector('#sv-pas-raqam').value.trim(),
    guvohnoma_raqami: content.querySelector('#sv-guv-raqam').value.trim(),
    guvohnoma_sanasi: content.querySelector('#sv-guv-sana').value.trim(),
    vafot_sababi: content.querySelector('#sv-sabab').value.trim(),
    shartnoma_bandi: content.querySelector('#sv-band').value.trim(),
    sugurta_shartnoma_raqami: content.querySelector('#sv-sh-raqam').value.trim(),
    sugurta_shartnoma_sanasi: content.querySelector('#sv-sh-sana').value.trim(),
    sugurta_kompaniya: content.querySelector('#sv-kompaniya').value.trim(),
    polis_raqami: content.querySelector('#sv-polis-raqam').value.trim(),
    polis_sanasi: content.querySelector('#sv-polis-sana').value.trim(),
    ariza_raqami: content.querySelector('#sv-ariza-raqam').value.trim(),
    ariza_sana: content.querySelector('#sv-ariza-sana').value.trim(),
    talab_summasi: content.querySelector('#sv-talab').value.trim(),
  });

  const saqla = async (xabar) => {
    const res = await fetch(`${API_BASE}/sugurta_undirish/saqlash`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(maydonlar()),
    });
    const dd = await res.json();
    if (dd.xato) { alert('Xato: ' + dd.xato); return false; }
    if (xabar) alert("Ma'lumotlar saqlandi.");
    return true;
  };

  content.querySelector('#sv-saqlash').addEventListener('click', async () => {
    if (await saqla(true)) await sugurtaVafotModalniChizish(anketa, overlay);
  });

  content.querySelector('#sv-ariza-yaratish').addEventListener('click', async () => {
    if (!content.querySelector('#sv-kompaniya').value.trim()) {
      alert("Avval sug'urta kompaniyasi nomini kiriting."); return;
    }
    await saqla(false);
    const res = await fetch(`${API_BASE}/sugurta_undirish/vafot_ariza_yaratish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anketa_raqami: anketa, format: content.querySelector('#sv-format').value }),
    });
    const dd = await res.json();
    if (dd.xato) { alert('Xato: ' + dd.xato); return; }
    alert("Ariza tayyorlandi. Tekshirib, kerak bo'lsa tahrirlang, so'ng 'Ariza yuborildi' deb belgilang.");
    await sugurtaVafotModalniChizish(anketa, overlay);
  });

  content.querySelector('#sv-qosh-yuklash').addEventListener('click', async () => {
    const nomi = content.querySelector('#sv-qosh-nomi').value.trim();
    const f = content.querySelector('#sv-qosh-file').files[0];
    if (!nomi || !f) { alert('Hujjat nomini yozing va faylni biriktiring.'); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('ish_turi', 'vafot');
    fd.append('tur', 'qoshimcha');
    fd.append('hujjat_nomi', nomi);
    fd.append('file', f);
    const res = await fetch(`${API_BASE}/sugurta_undirish/hujjat_yuklash`, { method: 'POST', body: fd });
    const dd = await res.json();
    if (dd.xato) { alert('Xato: ' + dd.xato); return; }
    await sugurtaVafotModalniChizish(anketa, overlay);
  });

  content.querySelectorAll('[data-sv-hujjat]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm("Bu hujjatni o'chirasizmi?")) return;
      await fetch(`${API_BASE}/sugurta_undirish/hujjat/${btn.dataset.svHujjat}`, { method: 'DELETE' });
      await sugurtaVafotModalniChizish(anketa, overlay);
    });
  });

  content.querySelectorAll('[data-sv-holat]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const holat = btn.dataset.svHolat;
      await saqla(false);
      const fd = new FormData();
      fd.append('anketa_raqami', anketa);
      fd.append('ish_turi', 'vafot');
      fd.append('holati', holat);
      fd.append('izoh', content.querySelector('#sv-izoh').value.trim());
      fd.append('sugurta_kompaniya', content.querySelector('#sv-kompaniya').value.trim());
      fd.append('polis_raqami', content.querySelector('#sv-polis-raqam').value.trim());
      fd.append('ariza_raqami', content.querySelector('#sv-ariza-raqam').value.trim());
      fd.append('ariza_sana', content.querySelector('#sv-ariza-sana').value.trim());
      if (holat === 'tolandi') {
        const summa = content.querySelector('#sv-tolangan').value.trim();
        if (!summa) { alert("To'langan summani kiriting."); return; }
        fd.append('tolangan_summa', summa);
        fd.append('tolov_sana', content.querySelector('#sv-tolov-sana').value.trim());
      }
      if (holat === 'rad_etildi' && !content.querySelector('#sv-izoh').value.trim()) {
        alert('Rad etish sababini yozing.'); return;
      }
      const nf = content.querySelector('#sv-natija-file').files[0];
      if (nf) fd.append('natija_fayl', nf);
      const res = await fetch(`${API_BASE}/sugurta_undirish/holat`, { method: 'POST', body: fd });
      const dd = await res.json();
      if (dd.xato) { alert('Xato: ' + dd.xato); return; }
      await sugurtaVafotModalniChizish(anketa, overlay);
    });
  });
}

async function sugurtaRoyxatniChizish() {
  const body = document.getElementById('sug-body');
  const data = await apiGet('/sugurta_undirish/royxat');

  let royxat = data.royxat;
  if (sugurtaHolatFiltr) royxat = royxat.filter(r => r.holati === sugurtaHolatFiltr);
  if (sugurtaQidiruv) {
    const q = sugurtaQidiruv.toLowerCase();
    royxat = royxat.filter(r => String(r.anketa_raqami).toLowerCase().includes(q)
      || String(r.mijoz_nomi).toLowerCase().includes(q)
      || String(r.mib_ish_raqami).toLowerCase().includes(q));
  }

  // MUHIM: holatlar jarayon TARTIBIDA ko'rsatiladi (alifbo bo'yicha emas):
  // Tayyorlanmoqda → Ariza yuborildi → To'landi → Rad etildi.
  const HOLAT_TARTIBI = ['tayyorlanmoqda', 'yuborildi', 'tolandi', 'rad_etildi'];
  const kartalar = HOLAT_TARTIBI.filter(k => data.holat_nomlari[k]).map(kod => {
    const nomi = data.holat_nomlari[kod];
    const soni = data.soni[kod] || 0;
    const faol = sugurtaHolatFiltr === kod;
    return `<button class="btn ${faol ? '' : 'ghost'}" data-sug-filtr="${kod}"
      style="${faol ? 'background:var(--navy);color:#fff;' : ''}">${nomi}: ${soni}</button>`;
  }).join('');

  const jamiTolangan = data.royxat.reduce((s, r) => s + (r.tolangan_summa || 0), 0);

  body.innerHTML = `
    <div class="toolbar">
      <input class="tb-input" id="sug-qidiruv" placeholder="Anketa, mijoz yoki MIB ish raqami"
        style="width:250px;" value="${sugurtaQidiruv}">
      <button class="btn" id="sug-qidir">🔍 Topish</button>
      ${sugurtaQidiruv ? '<button class="btn ghost" id="sug-qidiruv-tozalash">✕ Tozalash</button>' : ''}
      <button class="btn-gold" id="sug-excel" style="margin-left:auto;">📊 Excelga eksport</button>
    </div>
    <div class="toolbar">
      <button class="btn ${sugurtaHolatFiltr === '' ? '' : 'ghost'}" data-sug-filtr=""
        style="${sugurtaHolatFiltr === '' ? 'background:var(--navy);color:#fff;' : ''}">Barchasi: ${data.royxat.length}</button>
      ${kartalar}
      ${jamiTolangan > 0 ? `<div style="margin-left:auto; font-weight:700; color:#1E6B2E;">
        Sug'urtadan undirilgan: ${formatSum(jamiTolangan)} so'm</div>` : ''}
    </div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th>Anketa №</th><th>Mijoz</th><th>Jami qarz</th>
            <th>MIB ishi</th><th>MIB asos hujjati</th><th>Sug'urta kompaniyasi</th>
            <th>Holati</th><th>Talab / To'langan</th><th></th>
          </tr></thead>
          <tbody>
            ${royxat.map(r => `<tr>
              <td>${r.anketa_raqami}</td>
              <td style="max-width:170px;"><div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${String(r.mijoz_nomi).replace(/"/g, '&quot;')}">${xavfsizMatn(r.mijoz_nomi)}</div>
                <span style="font-size:11px;color:var(--muted);">${r.pinfl_stir}</span></td>
              <td style="white-space:nowrap;">${formatSum(r.jami_qarz)}</td>
              <td style="white-space:nowrap;">${r.mib_ish_raqami || '—'}<br><span style="font-size:11px;color:var(--muted);">${r.mib_otkazilgan_sana || ''} · ${r.mib_yakunlangan ? "✓ yakunlangan" : "⏳ jarayonda"}</span></td>
              <td style="max-width:175px;">${r.mib_asos_bor
                ? `<div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${String(r.mib_asos_hujjat_nomi || '').replace(/"/g, '&quot;')}">📎 ${r.mib_asos_hujjat_nomi || 'Yuklangan'}</div>`
                : '<span style="color:var(--muted);">— yuklanmagan</span>'}</td>
              <td style="max-width:150px;"><div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${r.sugurta_kompaniya || '—'}</div>${r.polis_raqami ? `<span style="font-size:11px;color:var(--muted);">${r.polis_raqami}</span>` : ''}</td>
              <td style="font-weight:600; white-space:nowrap;">${r.holat_nomi}
                ${r.kechikkan ? `<br><span style="font-size:11px;color:var(--err);">⚠ ${r.kutilgan_kun} kun javob yo'q</span>` : ''}
                ${r.qarz_yopilgan && r.holati === 'tayyorlanmoqda'
                  ? `<br><span style="font-size:11px;color:#1E6B2E;font-weight:400;">✓ Qarz yopilgan — ariza kerak emas</span>` : ''}</td>
              <td>${r.talab_summasi ? formatSum(r.talab_summasi) : '—'}
                ${r.tolangan_summa ? `<br><span style="color:#1E6B2E;font-weight:600;">✓ ${formatSum(r.tolangan_summa)}</span>` : ''}</td>
              <td style="white-space:nowrap;"><button class="btn-gold" data-sug-anketa="${r.anketa_raqami}"
                style="padding:4px 10px; font-size:11.5px; margin-left:0;">🛡 Ochish</button></td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
    ${royxat.length === 0 ? '<div class="page-sub" style="margin-top:12px;">Bu holatda ish topilmadi.</div>' : ''}
  `;

  body.querySelectorAll('[data-sug-filtr]').forEach(btn => {
    btn.addEventListener('click', () => { sugurtaHolatFiltr = btn.dataset.sugFiltr; sugurtaRoyxatniChizish(); });
  });
  const qidirBajar = () => {
    sugurtaQidiruv = document.getElementById('sug-qidiruv').value.trim();
    sugurtaRoyxatniChizish();
  };
  document.getElementById('sug-qidir').addEventListener('click', qidirBajar);
  document.getElementById('sug-qidiruv').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') qidirBajar();
  });
  const tozalaBtn = document.getElementById('sug-qidiruv-tozalash');
  if (tozalaBtn) tozalaBtn.addEventListener('click', () => { sugurtaQidiruv = ''; sugurtaRoyxatniChizish(); });
  document.getElementById('sug-excel').addEventListener('click', () => {
    tayyorJildYuklabOlish(`${API_BASE}/sugurta_undirish/excel`);
  });
  body.querySelectorAll('[data-sug-anketa]').forEach(btn => {
    btn.addEventListener('click', () => sugurtaDialogOchish(btn.dataset.sugAnketa));
  });
}

function sugurtaDialogOchish(anketa) {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(20,27,77,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;';
  overlay.innerHTML = `<div style="background:#fff;border-radius:12px;padding:20px 24px;width:800px;max-height:88vh;overflow-y:auto;" id="sug-modal"><div class="loading">Yuklanmoqda...</div></div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', async (e) => {
    if (e.target === overlay) { overlay.remove(); await sugurtaRoyxatniChizish(); }
  });
  sugurtaModalniChizish(anketa, overlay);
}

async function sugurtaModalniChizish(anketa, overlay) {
  const content = overlay.querySelector('#sug-modal');
  const d = await apiGet(`/sugurta_undirish/malumot?anketa=${encodeURIComponent(anketa)}`);
  if (d.xato) { content.innerHTML = `<div class="page-sub" style="color:var(--err);">${d.xato}</div>`; return; }
  const x = d.xat;
  const u = d.undirish || {};
  const joriyHolat = u.holati || 'tayyorlanmoqda';
  const fayl = (yol) => `<a href="${API_BASE}/fayl_korish?yol=${encodeURIComponent(yol)}" target="_blank">👁 Ko'rish</a>`;

  content.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
      <div style="font-size:16px; font-weight:700;">🛡 Sug'urtadan undirish — ${xavfsizMatn(x.mijoz_nomi)}</div>
      <button class="btn" id="sug-yopish">✕</button>
    </div>
    <div class="page-sub" style="margin-bottom:12px;">
      Anketa ${anketa} · Holati: <b>${d.holat_nomlari[joriyHolat] || joriyHolat}</b>
    </div>

    <div class="card" style="margin-bottom:10px;">
      <div class="card-h">🏛 MIB ijro ishi ma'lumotlari</div>
      <table style="width:100%; font-size:12.5px;">
        <tr><td style="width:40%; color:var(--muted); padding:3px 0;">MIB ish raqami</td>
            <td style="font-weight:600;">${x.mib_ish_raqami || '—'}</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">MIBga o'tkazilgan sana</td>
            <td style="font-weight:600;">${x.mib_otkazilgan_sana || '—'}</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">MIB holati</td>
            <td style="font-weight:600;">${x.mib_yakunlangan
              ? `✓ Yakunlangan (${x.mib_yakunlangan_sana || '—'})${x.mib_yakunlash_sababi ? ' — ' + x.mib_yakunlash_sababi : ''}`
              : '⏳ Jarayonda'}</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">Jami qarz</td>
            <td style="font-weight:600;">${formatSum(x.jami_qarz)} so'm</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">MIB orqali undirilgan</td>
            <td style="font-weight:600;">${formatSum(x.undirilgan_summa)} so'm</td></tr>
        <tr><td style="color:var(--muted); padding:3px 0;">Undirilmagan qoldiq</td>
            <td style="font-weight:700; color:var(--err);">${formatSum(x.qoldiq)} so'm</td></tr>
        ${x.ijro_varaqasi_fayl ? `<tr><td style="color:var(--muted); padding:3px 0;">Ijro varaqasi</td><td>${fayl(x.ijro_varaqasi_fayl)}</td></tr>` : ''}
        ${x.sud_qaror_fayl ? `<tr><td style="color:var(--muted); padding:3px 0;">Sud qarori</td><td>${fayl(x.sud_qaror_fayl)}</td></tr>` : ''}
        ${x.mib_yakunlash_hujjati_fayl ? `<tr><td style="color:var(--muted); padding:3px 0;">MIB yakunlash hujjati</td><td>${fayl(x.mib_yakunlash_hujjati_fayl)}</td></tr>` : ''}
      </table>
      ${d.mib_harakatlari.length > 0 ? `
        <div style="margin-top:8px; font-size:12px; color:var(--muted);">MIB harakatlari (asos hujjatni shu yerdan tanlashingiz mumkin):</div>
        <table style="width:100%; font-size:12px;">
          ${d.mib_harakatlari.map(h => `<tr>
            <td style="padding:3px 0;">${h.amal_sanasi || ''} — ${h.amal_turi || ''}</td>
            <td style="width:90px;">${h.dalolatnoma_fayl ? fayl(h.dalolatnoma_fayl) : ''}</td>
          </tr>`).join('')}
        </table>` : ''}
    </div>

    <div class="card" style="margin-bottom:10px; border-left:3px solid var(--gold);">
      <div class="card-h">📜 MIB chiqargan ASOS hujjat (majburiy)</div>
      <div class="page-sub" style="margin-bottom:8px;">
        Sug'urtadan undirish aynan shu hujjatga asoslanadi — masalan
        "undirib bo'lmaganligi to'g'risidagi dalolatnoma" yoki "ijro hujjatini
        qaytarish to'g'risidagi qaror". Hujjat nomini o'zingiz yozasiz.
      </div>
      ${u.mib_asos_fayl ? `<div style="font-size:12.5px; margin-bottom:8px; color:#1E6B2E;">
        ✓ Asos hujjat yuklangan &nbsp; ${fayl(u.mib_asos_fayl)}</div>` : ''}
      <div class="btn-row" style="margin-bottom:8px;">
        <input class="tb-input" id="sug-asos-nomi" placeholder="Hujjat nomi"
          style="width:300px;" value="${(u.mib_asos_hujjat_nomi || '').replace(/"/g, '&quot;')}">
        <input class="tb-input" id="sug-asos-raqam" placeholder="Hujjat raqami"
          style="width:150px;" value="${(u.mib_asos_hujjat_raqami || '').replace(/"/g, '&quot;')}">
        <input class="tb-input" id="sug-asos-sana" placeholder="Sanasi (kk.oo.yyyy)"
          style="width:150px;" value="${u.mib_asos_hujjat_sanasi || ''}">
      </div>
      <div class="btn-row">
        <input type="file" id="sug-asos-file" style="width:220px;">
        <button class="btn-gold" id="sug-asos-yuklash" style="margin-left:0;">📤 Asos hujjatni yuklash</button>
      </div>
    </div>

    <div class="card" style="margin-bottom:10px;">
      <div class="card-h">🛡 Sug'urta polisi va ariza</div>
      <div class="btn-row" style="margin-bottom:8px;">
        <input class="tb-input" id="sug-kompaniya" list="sug-kompaniyalar" placeholder="Sug'urta kompaniyasi"
          style="width:250px;" value="${(u.sugurta_kompaniya || '').replace(/"/g, '&quot;')}">
        <datalist id="sug-kompaniyalar">
          ${d.kompaniyalar.map(k => `<option value="${k.replace(/"/g, '&quot;')}">`).join('')}
        </datalist>
        <input class="tb-input" id="sug-polis-raqam" placeholder="Polis raqami"
          style="width:170px;" value="${(u.polis_raqami || '').replace(/"/g, '&quot;')}">
        <input class="tb-input" id="sug-polis-sana" placeholder="Polis sanasi"
          style="width:140px;" value="${u.polis_sanasi || ''}">
      </div>
      <div class="btn-row" style="margin-bottom:8px;">
        <input class="tb-input" id="sug-ariza-raqam" placeholder="Ariza raqami"
          style="width:170px;" value="${(u.ariza_raqami || '').replace(/"/g, '&quot;')}">
        <input class="tb-input" id="sug-ariza-sana" placeholder="Ariza sanasi"
          style="width:140px;" value="${u.ariza_sana || ''}">
        <input class="tb-input" id="sug-talab" placeholder="Talab summasi"
          style="width:170px;" value="${u.talab_summasi || ''}">
        <button class="btn" id="sug-saqlash" style="margin-left:0;">💾 Saqlash</button>
      </div>
      <div class="btn-row" style="margin-bottom:8px;">
        <select class="tb-select" id="sug-hujjat-turi" style="width:220px;">
          <option value="polis">Sug'urta polisi</option>
          <option value="ariza">Sug'urta kompaniyasiga ariza</option>
        </select>
        <input type="file" id="sug-hujjat-file" style="width:200px;">
        <button class="btn-gold" id="sug-hujjat-yuklash" style="margin-left:0;">📤 Yuklash</button>
      </div>
      <div style="background:#F4F6FB; border-radius:8px; padding:10px 12px;">
        <div style="font-size:12.5px; font-weight:600; margin-bottom:6px;">
          📝 Arizani tizim o'zi tayyorlab beradi (shablon asosida)
        </div>
        <div class="page-sub" style="margin-bottom:8px;">
          "Sug'urta tovonini to'lash to'g'risida"gi ariza shablonini mijoz, kredit shartnomasi,
          sud qarori va polis ma'lumotlari bilan to'ldiradi. Shablonni Sozlamalar →
          Sug'urtadan undirish bo'limida yangilashingiz mumkin.
        </div>
        <div class="btn-row">
          <select class="tb-select" id="sug-ariza-format" style="width:130px;">
            <option value="docx">Word (.docx)</option>
            <option value="pdf">PDF</option>
          </select>
          <button class="btn-gold" id="sug-ariza-yaratish" style="margin-left:0;">📝 Ariza tayyorlash</button>
        </div>
      </div>
      <div style="font-size:12.5px; margin-top:8px;">
        ${u.polis_fayl ? `✓ Polis yuklangan ${fayl(u.polis_fayl)} &nbsp;&nbsp;` : ''}
        ${u.ariza_fayl ? `✓ Ariza yuklangan ${fayl(u.ariza_fayl)}` : ''}
      </div>
    </div>

    <div class="card" style="margin-bottom:10px;">
      <div class="card-h">📎 Ilova hujjatlar</div>
      <div class="page-sub" style="margin-bottom:8px;">
        Sud va MIB bosqichida yuklangan hujjatlarni (kredit shartnomasi, talabnoma,
        da'vo ariza, sud qarori, garov/kafillik, ijro varaqasi, MIB dalolatnomalari)
        tizim <b>o'zi topib qo'shadi</b> — oldingi sikllardan va arxivdan ham qidiradi.
        ${d.avto_qoshildi > 0 ? `<br><span style="color:#1E6B2E;font-weight:600;">✓ Hozir ${d.avto_qoshildi} ta hujjat avtomatik qo'shildi.</span>` : ''}
      </div>
      ${d.hujjatlar.length > 0 ? `
        <table style="width:100%; font-size:12.5px; margin-bottom:8px;">
          ${d.hujjatlar.map(h => `<tr>
            <td style="padding:4px 0;">${xavfsizMatn(h.hujjat_nomi)}</td>
            <td style="width:90px;">${fayl(h.fayl_yoli)}</td>
            <td style="width:50px;"><button class="btn danger" data-sug-hujjat="${h.id}" style="padding:2px 8px; font-size:11px;">🗑</button></td>
          </tr>`).join('')}
        </table>` : '<div class="page-sub">Hali hujjat biriktirilmagan.</div>'}
      <div class="btn-row" style="margin-top:8px;">
        <button class="btn" id="sug-yigish" style="margin-left:0;">🔄 Hujjatlarni qayta yig'ish</button>
      </div>
      <div class="btn-row" style="margin-top:8px;">
        <input class="tb-input" id="sug-qosh-nomi" placeholder="Hujjat nomi (o'zingiz yozasiz)" style="width:300px;">
        <input type="file" id="sug-qosh-file" style="width:190px;">
        <button class="btn-gold" id="sug-qosh-yuklash" style="margin-left:0;">📤 Qo'shish</button>
      </div>
    </div>

    <div class="card">
      <div class="card-h">🔄 Holati</div>
      <div class="btn-row" style="margin-bottom:10px;">
        <button class="btn-gold" data-sug-holat="yuborildi" style="margin-left:0;">📤 Ariza yuborildi</button>
        <button class="btn" data-sug-holat="tolandi" style="background:#1E6B2E;color:#fff;">✓ To'landi</button>
        <button class="btn danger" data-sug-holat="rad_etildi">✕ Rad etildi</button>
      </div>
      <div class="btn-row" style="margin-bottom:8px; align-items:flex-end;">
        <label style="font-size:11.5px; color:var(--muted);">To'langan summa<br>
          <input class="tb-input" id="sug-tolangan" placeholder="masalan: 98000000"
            style="width:180px;" value="${u.tolangan_summa || ''}"></label>
        <label style="font-size:11.5px; color:var(--muted);">To'lov sanasi<br>
          <input class="tb-input" id="sug-tolov-sana" placeholder="kk.oo.yyyy"
            style="width:140px;" value="${u.tolov_sana || ''}"></label>
        <label style="font-size:11.5px; color:var(--muted);">Javob hujjati (ixtiyoriy)<br>
          <input type="file" id="sug-natija-file" style="width:200px;"></label>
      </div>
      <label style="display:block; font-size:12.5px;">Izoh (rad etilsa — sababi majburiy)<br>
        <textarea class="tb-input" id="sug-izoh" style="width:100%;" rows="2">${u.natija_izoh || ''}</textarea></label>
      ${u.natija_fayl ? `<div style="font-size:12.5px; margin-top:6px;">✓ Javob hujjati ${fayl(u.natija_fayl)}</div>` : ''}
    </div>
  `;

  content.querySelector('#sug-yopish').addEventListener('click', async () => {
    overlay.remove();
    await sugurtaRoyxatniChizish();
  });

  // Matn maydonlarini saqlash
  const maydonlarniYigish = () => ({
    anketa_raqami: anketa, ish_turi: 'mib',
    sugurta_kompaniya: content.querySelector('#sug-kompaniya').value.trim(),
    polis_raqami: content.querySelector('#sug-polis-raqam').value.trim(),
    polis_sanasi: content.querySelector('#sug-polis-sana').value.trim(),
    mib_asos_hujjat_nomi: content.querySelector('#sug-asos-nomi').value.trim(),
    mib_asos_hujjat_raqami: content.querySelector('#sug-asos-raqam').value.trim(),
    mib_asos_hujjat_sanasi: content.querySelector('#sug-asos-sana').value.trim(),
    ariza_raqami: content.querySelector('#sug-ariza-raqam').value.trim(),
    ariza_sana: content.querySelector('#sug-ariza-sana').value.trim(),
    talab_summasi: content.querySelector('#sug-talab').value.trim(),
  });

  const saqla = async (xabarBilan) => {
    const res = await fetch(`${API_BASE}/sugurta_undirish/saqlash`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(maydonlarniYigish()),
    });
    const dd = await res.json();
    if (dd.xato) { alert('Xato: ' + dd.xato); return false; }
    if (xabarBilan) alert("Ma'lumotlar saqlandi.");
    return true;
  };

  content.querySelector('#sug-saqlash').addEventListener('click', async () => {
    if (await saqla(true)) await sugurtaModalniChizish(anketa, overlay);
  });

  // MIB asos hujjatini yuklash — nomi bilan birga saqlanadi
  content.querySelector('#sug-asos-yuklash').addEventListener('click', async () => {
    const f = content.querySelector('#sug-asos-file').files[0];
    const nomi = content.querySelector('#sug-asos-nomi').value.trim();
    if (!f) { alert('Faylni biriktiring.'); return; }
    if (!nomi) { alert("Hujjat nomini yozing (masalan: Undirib bo'lmaganligi to'g'risidagi dalolatnoma)."); return; }
    await saqla(false);
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('ish_turi', 'mib');
    fd.append('tur', 'mib_asos');
    fd.append('hujjat_nomi', nomi);
    fd.append('file', f);
    const res = await fetch(`${API_BASE}/sugurta_undirish/hujjat_yuklash`, { method: 'POST', body: fd });
    const dd = await res.json();
    if (dd.xato) { alert('Xato: ' + dd.xato); return; }
    await sugurtaModalniChizish(anketa, overlay);
  });

  // Arizani shablon asosida avtomatik tayyorlash
  content.querySelector('#sug-ariza-yaratish').addEventListener('click', async () => {
    if (!content.querySelector('#sug-kompaniya').value.trim()) {
      alert("Avval sug'urta kompaniyasi nomini kiriting."); return;
    }
    await saqla(false);
    const res = await fetch(`${API_BASE}/sugurta_undirish/ariza_yaratish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        anketa_raqami: anketa,
        format: content.querySelector('#sug-ariza-format').value,
      }),
    });
    const dd = await res.json();
    if (dd.xato) { alert('Xato: ' + dd.xato); return; }
    alert("Ariza tayyorlandi. Tekshirib, kerak bo'lsa tahrirlang, so'ng 'Ariza yuborildi' deb belgilang.");
    await sugurtaModalniChizish(anketa, overlay);
  });

  content.querySelector('#sug-hujjat-yuklash').addEventListener('click', async () => {
    const tur = content.querySelector('#sug-hujjat-turi').value;
    const f = content.querySelector('#sug-hujjat-file').files[0];
    if (!f) { alert('Faylni biriktiring.'); return; }
    await saqla(false);
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('ish_turi', 'mib');
    fd.append('tur', tur);
    fd.append('file', f);
    const res = await fetch(`${API_BASE}/sugurta_undirish/hujjat_yuklash`, { method: 'POST', body: fd });
    const dd = await res.json();
    if (dd.xato) { alert('Xato: ' + dd.xato); return; }
    await sugurtaModalniChizish(anketa, overlay);
  });

  content.querySelector('#sug-yigish').addEventListener('click', async () => {
    const res = await fetch(`${API_BASE}/sugurta_undirish/hujjatlarni_yigish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anketa_raqami: anketa }),
    });
    const dd = await res.json();
    if (dd.xato) { alert('Xato: ' + dd.xato); return; }
    alert(dd.qoshildi > 0
      ? `${dd.qoshildi} ta yangi hujjat qo'shildi:\n\n• ${dd.nomlar.join('\n• ')}`
      : "Yangi hujjat topilmadi — barchasi allaqachon qo'shilgan.");
    await sugurtaModalniChizish(anketa, overlay);
  });

  content.querySelector('#sug-qosh-yuklash').addEventListener('click', async () => {
    const nomi = content.querySelector('#sug-qosh-nomi').value.trim();
    const f = content.querySelector('#sug-qosh-file').files[0];
    if (!nomi || !f) { alert('Hujjat nomini yozing va faylni biriktiring.'); return; }
    const fd = new FormData();
    fd.append('anketa_raqami', anketa);
    fd.append('ish_turi', 'mib');
    fd.append('tur', 'qoshimcha');
    fd.append('hujjat_nomi', nomi);
    fd.append('file', f);
    const res = await fetch(`${API_BASE}/sugurta_undirish/hujjat_yuklash`, { method: 'POST', body: fd });
    const dd = await res.json();
    if (dd.xato) { alert('Xato: ' + dd.xato); return; }
    await sugurtaModalniChizish(anketa, overlay);
  });

  content.querySelectorAll('[data-sug-hujjat]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm("Bu hujjatni o'chirasizmi?")) return;
      await fetch(`${API_BASE}/sugurta_undirish/hujjat/${btn.dataset.sugHujjat}`, { method: 'DELETE' });
      await sugurtaModalniChizish(anketa, overlay);
    });
  });

  content.querySelectorAll('[data-sug-holat]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const holat = btn.dataset.sugHolat;
      // Avval matn maydonlarini saqlab olamiz — xodim yozgan qiymatlar
      // yo'qolib ketmasligi uchun.
      await saqla(false);
      const fd = new FormData();
      fd.append('anketa_raqami', anketa);
      fd.append('ish_turi', 'mib');
      fd.append('holati', holat);
      fd.append('izoh', content.querySelector('#sug-izoh').value.trim());
      fd.append('sugurta_kompaniya', content.querySelector('#sug-kompaniya').value.trim());
      fd.append('polis_raqami', content.querySelector('#sug-polis-raqam').value.trim());
      fd.append('ariza_raqami', content.querySelector('#sug-ariza-raqam').value.trim());
      fd.append('ariza_sana', content.querySelector('#sug-ariza-sana').value.trim());
      if (holat === 'tolandi') {
        const summa = content.querySelector('#sug-tolangan').value.trim();
        if (!summa) { alert("To'langan summani kiriting."); return; }
        fd.append('tolangan_summa', summa);
        fd.append('tolov_sana', content.querySelector('#sug-tolov-sana').value.trim());
      }
      if (holat === 'rad_etildi' && !content.querySelector('#sug-izoh').value.trim()) {
        alert('Rad etish sababini yozing.'); return;
      }
      const nf = content.querySelector('#sug-natija-file').files[0];
      if (nf) fd.append('natija_fayl', nf);
      const res = await fetch(`${API_BASE}/sugurta_undirish/holat`, { method: 'POST', body: fd });
      const dd = await res.json();
      if (dd.xato) { alert('Xato: ' + dd.xato); return; }
      await sugurtaModalniChizish(anketa, overlay);
    });
  });
}
