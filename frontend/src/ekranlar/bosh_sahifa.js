// Bosh sahifa va "Bugungi vazifalar" paneli.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

async function boshSahifaniYuklash(main) {
  const [data, kunlik, tarixData, vazifalar] = await Promise.all([
    apiGet('/dashboard/summary'), apiGet('/reja/kunlik'), apiGet('/tahlil/tarix'),
    apiGet('/vazifalar/bugun').catch(() => ({ royxat: [], xulosa: null })),
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

    <div id="vazifalar-paneli"></div>

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
            <span>${xavfsizMatn(t.nomi)}</span><b>${t.bajarildi} / ${t.reja}</b>
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
      <tr><td>${r.sana}</td><td>${r.anketa_raqami}</td><td>${xavfsizMatn(r.mijoz_nomi)}</td><td>${r.xat_turi}</td><td>${r.holat_matni}</td>
        <td>
          ${vafotFaylKnop(r.xat_fayl, 'Xat')}
          ${r.davo_fayl ? ' &nbsp; ' + vafotFaylKnop(r.davo_fayl, 'Davo ariza') : ''}
          ${r.sud_buyrugi_fayl ? ' &nbsp; ' + vafotFaylKnop(r.sud_buyrugi_fayl, 'Sud buyrugi') : ''}
          ${r.ijro_varaqasi_fayl ? ' &nbsp; ' + vafotFaylKnop(r.ijro_varaqasi_fayl, 'Ijro varaqasi') : ''}
          ${r.yakunlash_fayl ? ' &nbsp; ' + vafotFaylKnop(r.yakunlash_fayl, 'Yakunlash asosi') : ''}
        </td>
      </tr>`).join('');
  });

  vazifalarPaneliniChizish(vazifalar);
}


// ═══ AQLLI YORDAMCHI — BUGUNGI VAZIFALAR ══════════════════════════════
// Tizim barcha bosqichlarni ko'rib chiqib, "bugun kimga nima qilish
// kerak" degan savolga javob beradi. Xodim har bir bo'limni alohida
// ochib, kim qayerda qolganini qidirib yurmaydi.

// ═══ AQLLI YORDAMCHI — BUGUNGI VAZIFALAR ══════════════════════════════
// Tizim barcha bosqichlarni ko'rib chiqib, "bugun kimga nima qilish
// kerak" degan savolga javob beradi. Xodim har bir bo'limni alohida
// ochib, kim qayerda qolganini qidirib yurmaydi.
const VAZIFA_USLUBI = {
  kechikkan: { belgi: '🔴', nomi: 'Kechikkan', rang: '#C0392B', fon: '#FDECEA' },
  bugun:     { belgi: '🟡', nomi: 'Shoshilinch', rang: '#B8860B', fon: '#FDF6E3' },
  rejali:    { belgi: '⚪', nomi: 'Rejali', rang: '#5A6480', fon: '#F4F6FB' },
};

function vazifalarPaneliniChizish(data) {
  const panel = document.getElementById('vazifalar-paneli');
  if (!panel || !data || !data.xulosa) return;
  const x = data.xulosa;

  if (x.jami === 0) {
    panel.innerHTML = `
      <div class="card" style="margin-bottom:18px; border-left:3px solid #1E6B2E;">
        <div class="card-h">✓ Bugungi vazifalar</div>
        <div class="page-sub">Kechiktirilgan ish yo'q — hamma narsa o'z vaqtida.</div>
      </div>`;
    return;
  }

  let royxat = data.royxat;
  if (vazifaFiltr) royxat = royxat.filter(v => v.ustuvorlik === vazifaFiltr);

  const karta = (kod) => {
    const u = VAZIFA_USLUBI[kod];
    const soni = x[kod] || 0;
    const faol = vazifaFiltr === kod;
    return `<button class="btn ${faol ? '' : 'ghost'}" data-vz-filtr="${kod}"
      style="${faol ? `background:${u.rang};color:#fff;border-color:${u.rang};` : ''}">
      ${u.belgi} ${xavfsizMatn(u.nomi)}: ${soni}</button>`;
  };

  panel.innerHTML = `
    <div class="card" style="margin-bottom:18px; ${x.kechikkan > 0 ? 'border-left:3px solid #C0392B;' : ''}">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div class="card-h" style="margin:0;">🎯 Bugungi vazifalar — ${x.jami} ta</div>
        <div style="font-size:12.5px; color:var(--muted);">
          Xavf ostidagi qarz: <b style="color:var(--err);">${formatSum(x.jami_qarz)} so'm</b>
        </div>
      </div>
      <div class="page-sub" style="margin-bottom:10px;">
        Tizim barcha bosqichlarni ko'rib chiqdi — har bir mijoz uchun keyingi qadam quyida,
        eng shoshilinchidan boshlab.
      </div>

      <div class="btn-row" style="margin-bottom:10px;">
        <button class="btn ${vazifaFiltr === '' ? '' : 'ghost'}" data-vz-filtr=""
          style="${vazifaFiltr === '' ? 'background:var(--navy);color:#fff;' : ''}">Barchasi: ${x.jami}</button>
        ${karta('kechikkan')} ${karta('bugun')} ${karta('rejali')}
        <button class="btn-gold" id="vz-excel" style="margin-left:auto;">📊 Excelga</button>
      </div>

      <div class="table-wrap"><div class="table-scroll" style="max-height:340px;">
        <table>
          <thead><tr>
            <th style="width:32px;"></th><th>Muddat</th><th>Anketa №</th><th>Mijoz</th>
            <th>Qarz</th><th>Bajariladigan ish</th><th>Izoh</th><th></th>
          </tr></thead>
          <tbody>
            ${royxat.map(v => {
              const u = VAZIFA_USLUBI[v.ustuvorlik];
              const kun = v.qolgan_kun === null || v.qolgan_kun === undefined ? '—'
                : v.qolgan_kun < 0 ? `<span style="color:${u.rang};font-weight:700;">${-v.qolgan_kun} kun kechikdi</span>`
                : v.qolgan_kun === 0 ? `<span style="color:${u.rang};font-weight:700;">Bugun</span>`
                : `${v.qolgan_kun} kun qoldi`;
              return `<tr style="background:${v.ustuvorlik === 'kechikkan' ? u.fon : 'transparent'};">
                <td style="text-align:center;">${u.belgi}</td>
                <td style="white-space:nowrap; font-size:12px;">${kun}</td>
                <td>${v.anketa_raqami}</td>
                <td style="max-width:170px;"><div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                     title="${String(v.mijoz_nomi).replace(/"/g, '&quot;')}">${xavfsizMatn(v.mijoz_nomi)}</div>
                  <span style="font-size:11px;color:var(--muted);">${v.pinfl_stir || ''}</span></td>
                <td style="white-space:nowrap;">${formatSum(v.qarz)}</td>
                <td style="font-weight:600;">${v.vazifa}</td>
                <td style="font-size:11.5px; color:var(--muted); max-width:220px;">
                  <div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                       title="${String(v.izoh || '').replace(/"/g, '&quot;')}">${v.izoh || ''}</div></td>
                <td style="white-space:nowrap;"><button class="btn" data-vz-bolim="${v.bolim}"
                    style="padding:3px 9px; font-size:11px;">${v.bolim_nomi} →</button></td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div></div>
      ${royxat.length === 0 ? '<div class="page-sub" style="margin-top:8px;">Bu turkumda vazifa yo\'q.</div>' : ''}
      ${x.chora_jami > x.chora_korsatildi ? `
        <div style="margin-top:10px; font-size:12.5px; color:var(--muted);">
          Bundan tashqari, <b>${formatSum(x.chora_jami - x.chora_korsatildi)}</b> ta mijozga chora ko'rish kerak
          (eng shoshilinch ${x.chora_korsatildi} tasi yuqorida).
          <button class="btn" data-vz-bolim="chora" style="padding:2px 8px; font-size:11px;">Chora ko'rish →</button>
        </div>` : ''}
    </div>`;

  panel.querySelectorAll('[data-vz-filtr]').forEach(btn => {
    btn.addEventListener('click', async () => {
      vazifaFiltr = btn.dataset.vzFiltr;
      vazifalarPaneliniChizish(data);
    });
  });
  panel.querySelectorAll('[data-vz-bolim]').forEach(btn => {
    btn.addEventListener('click', () => ekranniOchish(btn.dataset.vzBolim));
  });
  const excelBtn = panel.querySelector('#vz-excel');
  if (excelBtn) excelBtn.addEventListener('click', () => {
    tayyorJildYuklabOlish(`${API_BASE}/vazifalar/excel`);
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
          <div style="font-weight:600;">${xavfsizMatn(r.mijoz_nomi)} (${r.turi})</div>
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
