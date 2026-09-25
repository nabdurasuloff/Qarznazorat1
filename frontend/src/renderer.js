// Yadro — sidebar, API chaqiruvlari va umumiy yordamchilar.
// (ilgari renderer.js ichida edi — kod o'zgarmadi, faqat ajratildi)

// Qarz Nazorat — asosiy frontend mantiq. Sidebar navigatsiyasi va
// har bir ekranni backend API'dan ma'lumot olib ko'rsatish shu yerda.

const SIDEBAR_ITEMS = [
  { key: 'bosh_sahifa', icon: '🏠', label: 'Bosh sahifa' },
  { key: 'portfel', icon: '📁', label: 'Portfel' },
  { key: 'mijozlar', icon: '👥', label: 'Mijozlar bazasi' },
  { key: 'tahlil', icon: '📊', label: 'Tahlil' },
  { key: 'reja_grafik', icon: '📅', label: 'Reja Grafik' },
  { key: 'talabnoma', icon: '✉', label: 'Talabnoma' },
  { key: 'davo_ariza', icon: '📄', label: 'Davo Ariza' },
  { key: 'biznes_hamroh', icon: '🌐', label: 'Biznes-hamroh' },
  { key: 'sud', icon: '⚖', label: 'SUD Ishlari' },
  { key: 'mib', icon: '🏛', label: 'MIB ijro harakatlari' },
  { key: 'sugurta_undirish', icon: '🛡', label: "Sug'urtadan undirish" },
  { key: 'vafot', icon: '🕊', label: 'Vafot etganlar' },
  { key: '95413', icon: '📋', label: '95413' },
  { key: 'chora', icon: '🎯', label: "Chora ko'rish" },
  { key: 'sozlamalar', icon: '⚙️', label: 'Sozlamalar' },
];

let API_BASE = 'http://127.0.0.1:8877/api';

async function apiGet(path) {
  const r = await fetch(`${API_BASE}${path}`);
  if (!r.ok) throw new Error(`API xato: ${r.status}`);
  return r.json();
}

function ochiladiganMenyu(id, label, itemsHtml) {
  return `
    <div class="dropdown-wrap" style="position:relative; display:inline-block;">
      <button class="btn" id="${id}-btn">${label} ▾</button>
      <div class="dropdown-menu" id="${id}-menu" style="display:none; position:fixed; background:#fff; border:1px solid #E2E5EC; border-radius:8px; box-shadow:0 4px 16px rgba(0,0,0,0.12); padding:6px; min-width:230px; z-index:999;">
        ${itemsHtml}
      </div>
    </div>`;
}

function ochiladiganMenyuIshga(id) {
  const btn = document.getElementById(`${id}-btn`);
  const menu = document.getElementById(`${id}-menu`);
  if (!btn || !menu) return;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const ochiqmi = menu.style.display === 'block';
    document.querySelectorAll('.dropdown-menu').forEach(m => { m.style.display = 'none'; });
    if (!ochiqmi) {
      // MUHIM: menyu 'position:fixed' bo'lgani uchun, uni tugmaning
      // EKRANDAGI (skroll konteynerdan mustaqil) haqiqiy joylashuviga
      // qarab joylashtiramiz — aks holda jadval ichidagi skroll
      // konteynerlar uni "kesib" tashlab, ko'rinmas qilib qo'yardi.
      const rect = btn.getBoundingClientRect();
      menu.style.top = (rect.bottom + 4) + 'px';
      let left = rect.left;
      const oynaKengligi = window.innerWidth;
      if (left + 230 > oynaKengligi) left = Math.max(8, oynaKengligi - 240);
      menu.style.left = left + 'px';
      menu.style.display = 'block';
    }
  });
  document.addEventListener('click', (e) => {
    if (!menu.contains(e.target) && e.target !== btn) menu.style.display = 'none';
  });
}

function formatSum(n) {
  if (n === null || n === undefined) return '—';
  return Math.round(n).toLocaleString('ru-RU').replace(/,/g, ' ');
}

// ---------------- SIDEBAR ----------------
function sidebarQurish() {
  const container = document.getElementById('sb-items');
  container.innerHTML = '';
  SIDEBAR_ITEMS.forEach(item => {
    const el = document.createElement('div');
    el.className = 'sb-item';
    el.dataset.key = item.key;
    el.innerHTML = `<span>${item.icon}</span><span>${item.label}</span>`;
    el.addEventListener('click', () => ekranniOchish(item.key));
    container.appendChild(el);
  });
}

function faolBolimniBelgilash(key) {
  document.querySelectorAll('.sb-item').forEach(el => {
    el.classList.toggle('active', el.dataset.key === key);
  });
}

// ---------------- EKRANLAR ----------------
// Ekran xaritasi (EKRAN_YUKLOVCHILAR) ekranlar/app.js faylida —
// u eng oxirida yuklanadi, chunki barcha ekran funksiyalari
// o'z fayllarida aniqlanishi kerak.

async function ekranniOchish(key) {
  faolBolimniBelgilash(key);
  const main = document.getElementById('main-content');
  main.innerHTML = '<div class="loading">Yuklanmoqda...</div>';

  const yuklovchi = EKRAN_YUKLOVCHILAR[key];
  if (yuklovchi) {
    try {
      await yuklovchi(main);
    } catch (e) {
      main.innerHTML = `<div class="loading">Xato: ${e.message}</div>`;
    }
  } else {
    main.innerHTML = `<div class="page-title">${key}</div>
      <div class="page-sub">Bu bo'lim hali ishlab chiqilmoqda...</div>`;
  }
}

// ---------------- BOSH SAHIFA ----------------
// Bosh sahifadagi "Bugungi vazifalar" paneli qaysi ustuvorlikni ko'rsatmoqda

// ---------------- BOSH SAHIFA ----------------
// Bosh sahifadagi "Bugungi vazifalar" paneli qaysi ustuvorlikni ko'rsatmoqda
let vazifaFiltr = '';
