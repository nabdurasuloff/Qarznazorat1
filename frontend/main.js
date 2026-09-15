// Qarz Nazorat — Electron asosiy jarayoni.
// Bu fayl: (1) Python backend serverni fon jarayon sifatida ishga
// tushiradi, (2) asosiy oynani ochadi, (3) dastur yopilganda backend'ni
// ham to'xtatadi.

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, exec } = require('child_process');

const isDev = !app.isPackaged;
const BACKEND_PORT = 8877;

let backendProcess = null;
let mainWindow = null;

function konfigFayliYoli() {
    // MUHIM: bir nechta kompyuterni BITTA umumiy serverga ulash uchun —
    // har bir "mijoz" kompyuterda shu faylga serverning IP manzili
    // yoziladi. Bo'sh bo'lsa (standart holat) — bu kompyuter O'ZI server
    // (yoki mustaqil, yagona kompyuterli o'rnatma) hisoblanadi va o'z
    // backend.exe'sini ishga tushiradi.
    //
    // MUHIM TUZATISH: avval bu fayl .exe bilan bir papkada saqlanardi —
    // lekin agar dastur "Program Files" kabi HIMOYALANGAN (faqat admin
    // yoza oladigan) papkaga o'rnatilgan bo'lsa, yozish JIMGINA
    // muvaffaqiyatsiz tugab, sozlama saqlanmay qolar edi (va foydalanuvchi
    // buni bilmasdi). Endi doim yoziladigan, foydalanuvchiga tegishli
    // 'userData' papkasida saqlanadi.
    return path.join(app.getPath('userData'), 'tarmoq_sozlamasi.json');
}

function konfigOqish() {
    try {
        const yol = konfigFayliYoli();
        if (fs.existsSync(yol)) {
            return JSON.parse(fs.readFileSync(yol, 'utf-8'));
        }
    } catch (e) { console.error('Konfig oqishda xato:', e); }
    return { server_ip: '' };
}

function konfigYozish(konfig) {
    try {
        fs.writeFileSync(konfigFayliYoli(), JSON.stringify(konfig, null, 2), 'utf-8');
        return true;
    } catch (e) { console.error('Konfig yozishda xato:', e); return false; }
}

function backendYolini_topish() {
    if (isDev) {
        // Ishlab chiqish rejimida — tizimdagi python3 orqali to'g'ridan-to'g'ri
        return {
            komanda: 'python3',
            argumentlar: [path.join(__dirname, '..', 'backend', 'server.py')],
        };
    }
    // Qadoqlangan (.exe) holatda — PyInstaller bilan yig'ilgan backend.exe
    return {
        komanda: path.join(process.resourcesPath, 'backend', 'backend.exe'),
        argumentlar: [],
    };
}

function backendniIshgaTushirish() {
    const { komanda, argumentlar } = backendYolini_topish();
    backendProcess = spawn(komanda, argumentlar, {
        env: { ...process.env, PORT: String(BACKEND_PORT) },
        windowsHide: true, // Windows'da backend.exe konsol oynasi ko'rinmasin
    });
    backendProcess.stdout.on('data', (d) => console.log(`[backend] ${d}`));
    backendProcess.stderr.on('data', (d) => console.error(`[backend xato] ${d}`));
}

function oynaniOchish() {
    mainWindow = new BrowserWindow({
        width: 1450,
        height: 900,
        minWidth: 1100,
        minHeight: 700,
        backgroundColor: '#F4F6FB',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
        title: 'Qarz Nazorat va Talabnoma Tizimi',
    });
    mainWindow.loadFile(path.join(__dirname, 'index.html'));

    // MUHIM TUZATISH: renderer.js ko'p joyda window.open(url, '_blank') orqali
    // fayl yuklab olish/ko'rish (Excel, PDF, Word shablonlar) uchun murojaat
    // qiladi. Bu sozlama bo'lmasa, Electron har safar BO'SH, buzilgan yangi
    // ichki oyna ochib, klaviatura e'tiborini o'ziga tortib oladi — natijada
    // asosiy oynada matn kiritib bo'lmay qoladi. Endi bunday so'rovlar
    // o'rniga, fayl operatsion tizimning standart brauzerida ochiladi
    // (yuklab olish/ko'rish uchun to'g'ri va xavfsiz yo'l).
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    if (isDev) {
        // mainWindow.webContents.openDevTools();
    }
}

app.whenReady().then(() => {
    const konfig = konfigOqish();
    if (!konfig.server_ip) {
        // Bu kompyuter — SERVER (yoki mustaqil, yagona) rejimida: o'z
        // backend.exe'sini ishga tushiradi.
        backendniIshgaTushirish();
        setTimeout(oynaniOchish, 800); // backend ishga tushishi uchun kichik kutish
    } else {
        // Bu kompyuter — MIJOZ rejimida: o'z backend'ini ishga
        // tushirmaydi, boshqa (server) kompyuterdagi backend'ga ulanadi.
        oynaniOchish();
    }
});

function backendniToxtatish() {
    // MUHIM: backend.exe DASTUR OCHIQ TURGANDAgina ishlashi kerak — dastur
    // yopilganda albatta, ISHONCHLI ravishda to'xtatilishi shart (aks
    // holda orqa fonda "yetim" jarayon bo'lib qolib ketishi, va keyingi
    // safar dastur ochilganda eski (yangilanmagan) backend bilan
    // ulanib qolish xavfi bor edi). Oddiy .kill() ba'zan Windows'da
    // yetarli bo'lmasligi mumkin, shuning uchun 'taskkill /F /T' bilan
    // butun jarayon daraxtini majburan tugatamiz.
    if (!backendProcess) return;
    const pid = backendProcess.pid;
    if (process.platform === 'win32' && pid) {
        exec(`taskkill /PID ${pid} /T /F`, () => {});
    } else {
        try { backendProcess.kill(); } catch (e) {}
    }
    backendProcess = null;
}

app.on('window-all-closed', () => {
    backendniToxtatish();
    if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
    backendniToxtatish();
});

ipcMain.handle('backend-port', () => BACKEND_PORT);

ipcMain.handle('tarmoq-sozlamasi-olish', () => konfigOqish());

ipcMain.handle('tarmoq-sozlamasi-saqlash', (event, server_ip) => {
    const ok = konfigYozish({ server_ip: (server_ip || '').trim() });
    return ok;
});

ipcMain.handle('dasturni-qayta-ishga-tushirish', () => {
    app.relaunch();
    app.exit(0);
});
