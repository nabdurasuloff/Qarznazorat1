// Reja Grafik ekrani.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

// ---------------- REJA GRAFIK ----------------
let rejaSubTab = 'kunlik';

async function rejaGrafikniYuklash(main) {
  main.innerHTML = `
    <div class="page-title">Reja Grafik</div>
    <div class="page-sub">Bugungi kunda qilinishi kerak bo'lgan ishlar rejasi (xat, Davo ariza, MIB) va tarmoqlar kesimida bajarilgan ishlar hisoboti.</div>
    <div class="toolbar" style="margin-bottom:0;">
      <button class="btn ${rejaSubTab === 'kunlik' ? 'ghost' : ''}" id="reja-tab-kunlik"
        style="${rejaSubTab === 'kunlik' ? 'background:var(--navy);color:#fff;' : ''}">Kunlik ish rejasi</button>
      <button class="btn ${rejaSubTab === 'sudkunlari' ? 'ghost' : ''}" id="reja-tab-sudkunlari"
        style="${rejaSubTab === 'sudkunlari' ? 'background:var(--navy);color:#fff;' : ''}">⚖ Sud kunlari</button>
    </div>
    <div id="reja-body"></div>
  `;
  document.getElementById('reja-tab-kunlik').addEventListener('click', () => { rejaSubTab = 'kunlik'; rejaGrafikniYuklash(main); });
  document.getElementById('reja-tab-sudkunlari').addEventListener('click', () => { rejaSubTab = 'sudkunlari'; rejaGrafikniYuklash(main); });
  if (rejaSubTab === 'sudkunlari') await sudKunlariBoliminiChizish();
  else await rejaKunlikBoliminiChizish();
}

async function rejaKunlikBoliminiChizish() {
  const body = document.getElementById('reja-body');
  const [kunlik, tarmoqData] = await Promise.all([apiGet('/reja/kunlik'), apiGet('/reja/tarmoq')]);
  body.innerHTML = `
    <div class="card-h" style="margin-bottom:10px;">Bugungi ish rejasi (${kunlik.deadline} gacha, ${kunlik.ish_kunlari_qolgan} ish kuni qoldi)</div>
    <div class="card-row">
      ${kunlik.turkumlar.map(t => `
        <div class="card">
          <div class="card-h">${xavfsizMatn(t.nomi)}</div>
          <div style="display:flex; justify-content:space-between; font-size:13px; padding:4px 0;">
            <span>Kunlik reja:</span><b>${t.reja} ta</b></div>
          <div style="display:flex; justify-content:space-between; font-size:13px; padding:4px 0;">
            <span>Bajarildi:</span><b style="color:#1E6B2E;">${t.bajarildi} ta</b></div>
          <div style="display:flex; justify-content:space-between; font-size:13px; padding:4px 0;">
            <span>Qolib ketyapti:</span><b style="color:var(--err);">${t.qoldi} ta</b></div>
        </div>`).join('')}
    </div>

    <div class="card" style="margin-bottom:16px;">
      <div class="card-h">Kunlik ish rejasi umumiy bajarilishi</div>
      <div class="stat-num" style="color:${kunlik.foiz < 30 ? 'var(--err)' : '#1E6B2E'};">${kunlik.foiz}%</div>
      <div class="stat-label">${kunlik.umumiy_bajarildi} / ${kunlik.umumiy_reja} ta bajarildi (jami oy oxirigacha ish: ${kunlik.jami_ish} ta)</div>
    </div>

    <div class="card-h" style="margin-bottom:10px;">Tarmoq kesimida bajarilgan ishlar</div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr><th>Tarmoq</th><th>Jami xat</th><th>Yuborilgan</th><th>Davo ariza</th><th>Sudga o'tkazilgan</th><th>MIBga o'tkazilgan</th></tr></thead>
          <tbody>
            ${tarmoqData.tarmoq.map(r => `<tr>
              <td>${r.tarmoq}</td><td>${r.xat_soni}</td><td>${r.yuborilgan_soni || 0}</td>
              <td>${r.davo_soni || 0}</td><td>${r.sud_soni || 0}</td><td>${r.mib_soni || 0}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}
