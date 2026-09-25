// Tahlil ekrani — portfel va huquqiy jarayon tahlili.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

// ---------------- TAHLIL ----------------
// Tahlil bo'limining ochiq bo'limi: portfel yoki huquqiy jarayon
let tahlilTab = 'portfel';

async function tahlilniYuklash(main) {
  if (tahlilTab === 'jarayon') {
    await jarayonTahliliniYuklash(main);
    return;
  }
  const [t, tarixData] = await Promise.all([apiGet('/tahlil/umumiy'), apiGet('/tahlil/tarix')]);
  const tarix = tarixData.tarix;

  main.innerHTML = `
    <div class="page-title">Tahlil</div>
    ${tahlilTablariHtml()}
    <div class="page-sub">Butun portfel bo'yicha umumiy holat: jismoniy/yuridik taqsimoti, tarmoqlar kesimida va Stage 1/2/3 bo'yicha tahlil.</div>
    <div class="toolbar">
      <button class="btn" id="th-refresh">🔄 Yangilash</button>
      <span style="font-size:12.5px; color:var(--muted);">Format:</span>
      <select class="tb-select" id="th-format">
        <option value="word">Word (.docx)</option>
        <option value="pdf">PDF (.pdf)</option>
      </select>
      <button class="btn-gold" id="th-export" style="margin-left:0;">📄 Hisobotni yuklab olish</button>
    </div>

    <div class="stat-row">
      <div class="stat-card"><div class="stat-num">${formatSum(t.jami_soni)}</div><div class="stat-label">Jami portfeldagi mijozlar</div></div>
      <div class="stat-card"><div class="stat-num">${(t.jami_ead / 1e9).toFixed(1)} mlrd</div><div class="stat-label">Jami EAD qoldiq</div></div>
      <div class="stat-card"><div class="stat-num">${formatSum(t.jismoniy.soni)}</div><div class="stat-label">Jismoniy shaxslar (${(t.jismoniy.ead / 1e9).toFixed(1)} mlrd)</div></div>
      <div class="stat-card"><div class="stat-num">${formatSum(t.yuridik.soni)}</div><div class="stat-label">Yuridik shaxslar (${(t.yuridik.ead / 1e9).toFixed(1)} mlrd)</div></div>
    </div>

    <div class="card-row">
      <div class="card" style="flex:1;">
        <div class="card-h">Jismoniy / Yuridik taqsimoti (EAD bo'yicha)</div>
        <div style="position:relative; height:230px;"><canvas id="th-pie-chart"></canvas></div>
      </div>
      <div class="card" style="flex:1;">
        <div class="card-h">Stage 1 / 2 / 3 taqqoslash</div>
        <div style="position:relative; height:230px;"><canvas id="th-stage-chart"></canvas></div>
      </div>
    </div>

    <div class="card" style="margin-bottom:16px;">
      <div class="card-h">📈 Vaqt bo'yicha tendensiya — Stage 3 (yuqori xavfli) kreditlar soni</div>
      ${tarix.length < 2
        ? `<div class="page-sub" style="margin:0;">Hozircha faqat ${tarix.length} ta o'lchov mavjud. Portfelni har safar yangilaganingizda (Portfel bo'limi orqali) yangi nuqta avtomatik qo'shiladi — bir necha yangilanishdan keyin bu yerda haqiqiy tendensiya grafigi paydo bo'ladi.</div>`
        : `<div style="position:relative; height:220px;"><canvas id="th-trend-chart"></canvas></div>`
      }
    </div>

    <div class="card-h" style="margin-bottom:10px;">Tarmoq (soha) kesimida — EAD summasi bo'yicha
      <span style="font-weight:400; color:var(--muted); font-size:11px;">— qatorga bosib, mijozlar ro'yxatini ko'ring</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Tarmoq</th><th>Soni</th><th>EAD summasi</th></tr></thead>
        <tbody id="th-tarmoq-tbody">
          ${t.tarmoq.map(r => `<tr class="th-tarmoq-row" data-tarmoq="${r.tarmoq}" style="cursor:pointer;">
            <td>${r.tarmoq}</td><td>${formatSum(r.soni)}</td><td>${(r.ead / 1e9).toFixed(2)} mlrd</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  `;
  tahlilTablariniIshga(main);
  document.getElementById('th-refresh').addEventListener('click', () => tahlilniYuklash(main));
  document.getElementById('th-export').addEventListener('click', () => {
    const fmt = document.getElementById('th-format').value;
    faylniYuklabOlish(`${API_BASE}/tahlil/hisobot_yuklab_olish?format=${fmt}`);
  });

  document.querySelectorAll('.th-tarmoq-row').forEach(row => {
    row.addEventListener('mouseenter', () => row.style.background = '#EEF1FC');
    row.addEventListener('mouseleave', () => row.style.background = '');
    row.addEventListener('click', () => thTarmoqMijozlariDialogOchish(row.dataset.tarmoq));
  });

  // ---- Grafiklar (Chart.js) ----
  new Chart(document.getElementById('th-pie-chart'), {
    type: 'doughnut',
    data: {
      labels: ['Jismoniy shaxslar', 'Yuridik shaxslar'],
      datasets: [{ data: [t.jismoniy.ead / 1e9, t.yuridik.ead / 1e9], backgroundColor: ['#1E2761', '#C9A227'], borderWidth: 0 }],
    },
    options: { plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } }, maintainAspectRatio: false },
  });

  new Chart(document.getElementById('th-stage-chart'), {
    type: 'bar',
    data: {
      labels: t.stage.map(s => `Stage ${s.stage}`),
      datasets: [{ data: t.stage.map(s => s.soni), backgroundColor: ['#1E2761', '#C9A227', '#C0392B'], borderRadius: 6 }],
    },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } }, maintainAspectRatio: false },
  });

  if (tarix.length >= 2) {
    new Chart(document.getElementById('th-trend-chart'), {
      type: 'line',
      data: {
        labels: tarix.map(r => r.sana.slice(5)),
        datasets: [{ label: 'Stage 3 soni', data: tarix.map(r => r.stage3_soni),
          borderColor: '#C0392B', backgroundColor: 'rgba(192,57,43,0.08)', fill: true, tension: 0.3 }],
      },
      options: { plugins: { legend: { display: false } }, maintainAspectRatio: false },
    });
  }
}

// ═══ HUQUQIY JARAYON TAHLILI ══════════════════════════════════════════
// Mavjud "Tahlil" PORTFELNI tahlil qiladi; bu esa ISHNING O'ZINI:
// voronka, bosqich davomiyligi, undirish manbalari, oylik dinamika va
// MIB harakatlarining samaradorligi.
//
// Ranglar: uchta qatordagi (xat / sud / MIB) ranglar tekshiruvdan
// o'tkazilgan — rang ko'rish buzilishi (daltonizm) bo'lganda ham
// bir-biridan ajralib turadi, va oq fonda kontrasti yetarli.
const JARAYON_RANGLARI = { xat: '#3A5BC7', sud: '#B8860B', mib: '#1E7A4A' };

function tahlilTablariHtml() {
  const tab = (kod, nomi) => `<button class="btn ${tahlilTab === kod ? '' : 'ghost'}"
    data-th-tab="${kod}" style="${tahlilTab === kod ? 'background:var(--navy);color:#fff;' : ''}">${nomi}</button>`;
  return `<div style="display:flex; gap:8px; margin:10px 0 16px; flex-wrap:wrap;">
    ${tab('portfel', '📊 Portfel tahlili')}${tab('jarayon', '⚖ Huquqiy jarayon samaradorligi')}
  </div>`;
}

function tahlilTablariniIshga(main) {
  main.querySelectorAll('[data-th-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      tahlilTab = btn.dataset.thTab;
      tahlilniYuklash(main);
    });
  });
}

async function jarayonTahliliniYuklash(main) {
  main.innerHTML = `<div class="page-title">Tahlil</div>${tahlilTablariHtml()}
    <div class="loading">Hisoblanmoqda...</div>`;
  tahlilTablariniIshga(main);

  const h = await apiGet('/tahlil/jarayon');
  if (h.xato) {
    main.innerHTML += `<div class="page-sub" style="color:var(--err);">${h.xato}</div>`;
    return;
  }

  // Voronkada eng ko'p ish turgan bosqich — "tiqilish" joyi
  const engKop = Math.max(...h.voronka.map(v => v.soni), 1);
  const engKopSumma = Math.max(...h.voronka.map(v => v.summa), 1);

  // Davomiylikda eng uzun bosqich (to'liq yo'ldan tashqari) — tor joy
  const bosqichlar = h.davomiylik.filter(d => d.kod !== 'toliq' && d.soni > 0);
  const torJoy = bosqichlar.length
    ? bosqichlar.reduce((a, b) => (a.mediana > b.mediana ? a : b)) : null;
  const toliq = h.davomiylik.find(d => d.kod === 'toliq');

  const engKopUndirish = Math.max(...h.undirish.manbalar.map(m => m.summa), 1);

  main.innerHTML = `
    <div class="page-title">Tahlil</div>
    ${tahlilTablariHtml()}
    <div class="page-sub">Ishning o'zi qanday kechayotgani: qayerda tiqilib qolgan, qancha vaqt ketyapti va qaysi chora amalda pul qaytaryapti.</div>

    <div class="toolbar">
      <button class="btn" id="jt-yangilash">🔄 Yangilash</button>
      <span style="font-size:12.5px; color:var(--muted);">Hisob sanasi: ${h.sana}</span>
      <button class="btn-gold" id="jt-excel" style="margin-left:auto;">📊 Excel hisobot</button>
    </div>

    <div class="stat-row">
      <div class="stat-card">
        <div class="stat-num">${toliq && toliq.soni ? toliq.mediana : '—'}</div>
        <div class="stat-label">Xatdan ish yakuniga — o'rtacha kun${toliq && toliq.soni ? ` (${toliq.soni} ta ish)` : ''}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" style="color:#1E6B2E;">${formatSum(h.undirish.jami)}</div>
        <div class="stat-label">Jami undirilgan summa</div>
      </div>
      <div class="stat-card">
        <div class="stat-num ${torJoy ? 'warn' : ''}">${torJoy ? torJoy.mediana + ' kun' : '—'}</div>
        <div class="stat-label">Eng uzun bosqich${torJoy ? ': ' + torJoy.nomi.split('→')[0].trim() + ' →' : ''}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">${formatSum(h.voronka.reduce((s, v) => s + v.soni, 0))}</div>
        <div class="stat-label">Jarayondagi jami ishlar</div>
      </div>
    </div>

    <div class="card" style="margin-bottom:16px;">
      <div class="card-h">⏳ Voronka — hozir qaysi bosqichda nechta ish turibdi</div>
      <div class="page-sub" style="margin-bottom:10px;">Uzun qator — o'sha bosqichda ish to'planib qolgan degani.</div>
      <table style="width:100%; font-size:12.5px;">
        ${h.voronka.map(v => `<tr>
          <td style="width:42%; padding:5px 0;">${xavfsizMatn(v.nomi)}</td>
          <td style="width:42%;">
            <div style="background:var(--line); height:16px; border-radius:4px; overflow:hidden;">
              <div style="background:${JARAYON_RANGLARI.xat}; height:100%; border-radius:4px;
                          width:${Math.max(v.soni / engKop * 100, v.soni ? 3 : 0)}%;"></div>
            </div>
          </td>
          <td style="width:8%; text-align:right; font-weight:700; padding-left:10px;">${v.soni}</td>
          <td style="width:8%; text-align:right; color:var(--muted); white-space:nowrap; padding-left:10px;">
            ${v.summa ? formatSum(v.summa) : '—'}</td>
        </tr>`).join('')}
      </table>
    </div>

    <div class="card" style="margin-bottom:16px;">
      <div class="card-h">⏱ Bosqichlar qancha vaqt olayapti</div>
      <div class="page-sub" style="margin-bottom:10px;">
        Mediana — "odatdagi" ish qancha kun turadi (o'rtachadan ishonchliroq, chunki bitta cho'zilib
        ketgan ish uni buzmaydi). ${torJoy ? `Eng uzun bosqich <b style="color:var(--err);">${torJoy.nomi}</b> — ${torJoy.mediana} kun.` : ''}
      </div>
      <div class="table-wrap"><div class="table-scroll">
        <table>
          <thead><tr><th>Bosqich</th><th>Ishlar</th><th>Mediana</th><th>O'rtacha</th><th>Eng uzun</th><th></th></tr></thead>
          <tbody>
            ${h.davomiylik.map(d => {
              const eng = Math.max(...bosqichlar.map(b => b.mediana), 1);
              const torMi = torJoy && d.kod === torJoy.kod;
              return `<tr style="${d.kod === 'toliq' ? 'border-top:2px solid var(--line); font-weight:600;' : ''}">
                <td>${d.nomi}</td>
                <td>${d.soni || '—'}</td>
                <td style="font-weight:700; ${torMi ? 'color:var(--err);' : ''}">${d.soni ? d.mediana + ' kun' : '—'}</td>
                <td style="color:var(--muted);">${d.soni ? d.ortacha + ' kun' : '—'}</td>
                <td style="color:var(--muted);">${d.soni ? d.eng_uzun + ' kun' : '—'}</td>
                <td style="width:30%;">${d.soni && d.kod !== 'toliq' ? `
                  <div style="background:var(--line); height:12px; border-radius:3px; overflow:hidden;">
                    <div style="background:${torMi ? 'var(--err)' : JARAYON_RANGLARI.sud}; height:100%;
                                border-radius:3px; width:${Math.min(d.mediana / eng * 100, 100)}%;"></div>
                  </div>` : ''}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div></div>
    </div>

    <div class="card-row">
      <div class="card" style="flex:1;">
        <div class="card-h">💰 Pul qaysi yo'l bilan qaytdi</div>
        ${h.undirish.jami === 0 ? '<div class="page-sub">Hali undirilgan summa qayd etilmagan.</div>' : `
        <table style="width:100%; font-size:12.5px;">
          ${h.undirish.manbalar.filter(m => m.summa > 0).map(m => `<tr>
            <td style="width:40%; padding:5px 0;">${xavfsizMatn(m.nomi)}</td>
            <td style="width:35%;">
              <div style="background:var(--line); height:16px; border-radius:4px; overflow:hidden;">
                <div style="background:${JARAYON_RANGLARI.mib}; height:100%; border-radius:4px;
                            width:${m.summa / engKopUndirish * 100}%;"></div>
              </div>
            </td>
            <td style="text-align:right; font-weight:600; white-space:nowrap; padding-left:10px;">${formatSum(m.summa)}</td>
            <td style="text-align:right; color:var(--muted); width:52px;">${m.ulush}%</td>
          </tr>`).join('')}
          <tr style="border-top:2px solid var(--line);">
            <td style="padding-top:8px; font-weight:700;">JAMI</td><td></td>
            <td style="text-align:right; font-weight:700; color:#1E6B2E; padding-top:8px;">${formatSum(h.undirish.jami)}</td>
            <td></td>
          </tr>
        </table>`}
      </div>

      <div class="card" style="flex:1;">
        <div class="card-h">🏛 Qaysi MIB harakati ko'proq pul qaytaryapti</div>
        ${h.harakatlar.length === 0 ? '<div class="page-sub">Hali MIB harakatlari qayd etilmagan.</div>' : `
        <div class="table-scroll" style="max-height:260px;">
          <table>
            <thead><tr><th>Harakat turi</th><th>Soni</th><th>Jami</th><th>O'rtacha</th></tr></thead>
            <tbody>
              ${h.harakatlar.map(a => `<tr>
                <td>${a.amal_turi}</td>
                <td>${a.soni}</td>
                <td style="font-weight:600; white-space:nowrap;">${a.summa ? formatSum(a.summa) : '—'}</td>
                <td style="color:var(--muted); white-space:nowrap;">${a.ortacha ? formatSum(a.ortacha) : '—'}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
        <div class="page-sub" style="margin-top:8px;">Summasiz harakatlar ham kerak (qidiruv, xatlov) — ular keyingi choraga zamin bo'ladi.</div>`}
      </div>
    </div>

    <div class="card" style="margin-top:16px;">
      <div class="card-h">📈 Oylik dinamika — ish hajmi</div>
      <div class="page-sub" style="margin-bottom:8px;">Oyiga nechta xat yuborilgan, nechta ish sudga kiritilgan va MIBga o'tkazilgan.</div>
      <div style="position:relative; height:250px;"><canvas id="jt-hajm-chart"></canvas></div>
    </div>

    <div class="card" style="margin-top:16px;">
      <div class="card-h">📈 Oylik dinamika — undirilgan summa</div>
      <div class="page-sub" style="margin-bottom:8px;">Har oyda qancha pul qaytgani (MIB harakatlari va sug'urta to'lovlari).</div>
      <div style="position:relative; height:220px;"><canvas id="jt-pul-chart"></canvas></div>
    </div>
  `;

  tahlilTablariniIshga(main);
  document.getElementById('jt-yangilash').addEventListener('click', () => jarayonTahliliniYuklash(main));
  document.getElementById('jt-excel').addEventListener('click', () => {
    tayyorJildYuklabOlish(`${API_BASE}/tahlil/jarayon_excel`);
  });

  // MUHIM: ish hajmi (dona) va undirilgan summa (so'm) — ikki xil o'lchov.
  // Ularni BITTA grafikda ikki o'q bilan ko'rsatish yanglish taassurot
  // beradi, shuning uchun ATAYLAB ikkita alohida grafik chizilgan.
  const oylar = h.dinamika.map(d => d.oy);
  if (typeof Chart !== 'undefined') {
    new Chart(document.getElementById('jt-hajm-chart'), {
      type: 'line',
      data: {
        labels: oylar,
        datasets: [
          { label: 'Yuborilgan xatlar', data: h.dinamika.map(d => d.xat),
            borderColor: JARAYON_RANGLARI.xat, backgroundColor: JARAYON_RANGLARI.xat,
            borderWidth: 2, pointRadius: 4, pointHoverRadius: 6, tension: 0.25 },
          { label: 'Sudga kiritilgan', data: h.dinamika.map(d => d.sud),
            borderColor: JARAYON_RANGLARI.sud, backgroundColor: JARAYON_RANGLARI.sud,
            borderWidth: 2, pointRadius: 4, pointHoverRadius: 6, tension: 0.25 },
          { label: "MIBga o'tkazilgan", data: h.dinamika.map(d => d.mib),
            borderColor: JARAYON_RANGLARI.mib, backgroundColor: JARAYON_RANGLARI.mib,
            borderWidth: 2, pointRadius: 4, pointHoverRadius: 6, tension: 0.25 },
        ],
      },
      options: {
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, usePointStyle: true, font: { size: 11.5 } } },
          tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.y} ta` } },
        },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0, font: { size: 11 } },
               grid: { color: '#EEF1F7' }, title: { display: true, text: 'ishlar soni', font: { size: 11 } } },
          x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        },
      },
    });

    new Chart(document.getElementById('jt-pul-chart'), {
      type: 'bar',
      data: {
        labels: oylar,
        datasets: [{
          label: 'Undirilgan summa',
          data: h.dinamika.map(d => d.undirilgan),
          backgroundColor: JARAYON_RANGLARI.mib,
          borderRadius: 4, borderSkipped: false, maxBarThickness: 34,
        }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },   // bitta qator — sarlavha uni nomlaydi
          tooltip: { callbacks: { label: (c) => formatSum(c.parsed.y) + " so'm" } },
        },
        scales: {
          y: { beginAtZero: true, grid: { color: '#EEF1F7' },
               ticks: { font: { size: 11 }, callback: (v) => v >= 1e9 ? (v / 1e9).toFixed(1) + ' mlrd'
                        : v >= 1e6 ? Math.round(v / 1e6) + ' mln' : v } },
          x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        },
      },
    });
  }
}
