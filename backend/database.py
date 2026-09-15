# -*- coding: utf-8 -*-
"""
Ma'lumotlar bazasi (SQLite) bilan ishlash.
Dastur ishga tushganda 'qarz_nazorat.db' fayli avtomatik yaratiladi.
"""
import sqlite3
import os
import sys
import datetime
import hashlib
import re


def _app_dir():
    # .exe (PyInstaller --onefile) sifatida ishga tushganda ma'lumotlar bazasi
    # dastur fayli joylashgan papkada saqlanadi (vaqtinchalik _MEIPASS'da emas),
    # shunda dastur qayta ishga tushirilganda ma'lumotlar yo'qolmaydi.
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


DB_PATH = os.path.join(_app_dir(), 'qarz_nazorat.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS portfel (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        port_kod TEXT,
        anketa_raqami TEXT,
        unikal TEXT,
        stir TEXT,
        pinfl TEXT,
        filial_kodi TEXT,
        viloyat TEXT,
        tarmoq TEXT,
        stage TEXT,
        mijoz_turi_kodi TEXT,
        mijoz_turi TEXT,
        mijoz_nomi TEXT,
        valyuta TEXT,
        kredit_hisob_raqami TEXT,
        yillik_foiz REAL,
        shartnoma_sanasi TEXT,
        shartnoma_tugash_sanasi TEXT,
        tulov_maqsadi TEXT,
        dpd_asosiy INTEGER DEFAULT 0,
        dpd_foiz INTEGER DEFAULT 0,
        dpd_max INTEGER DEFAULT 0,
        ead REAL DEFAULT 0,
        jami_qarz REAL DEFAULT 0,
        asosiy_qarz REAL DEFAULT 0,
        foiz_qarz REAL DEFAULT 0,
        jarima REAL DEFAULT 0,
        balans_95413 REAL DEFAULT 0,
        import_sanasi TEXT,
        holat TEXT DEFAULT 'yangi',
        faol INTEGER DEFAULT 1,
        jami_berilgan_summa REAL
    )
    ''')

    # Eski bazalarda mavjud bo'lmasa, yangi ustunni qo'shib qo'yamiz
    existing_portfel_cols = {r['name'] for r in conn.execute("PRAGMA table_info(portfel)").fetchall()}
    if 'balans_95413' not in existing_portfel_cols:
        cur.execute('ALTER TABLE portfel ADD COLUMN balans_95413 REAL DEFAULT 0')
    if 'faol' not in existing_portfel_cols:
        cur.execute('ALTER TABLE portfel ADD COLUMN faol INTEGER DEFAULT 1')
    if 'jami_berilgan_summa' not in existing_portfel_cols:
        cur.execute('ALTER TABLE portfel ADD COLUMN jami_berilgan_summa REAL')

    # Порт_код bo'yicha noyob indeks — portfel yangilanganda (qayta import
    # qilinganda) mavjud kreditlar YANGILANADI (o'chirilmaydi), shunda
    # ularga bog'liq xatlar/Davo arizalar bog'lanishi buzilmaydi.
    # ("Анкета раками" filiallar orasida qayta ishlatilishi mumkin bo'lgani
    # uchun, "Порт_код" haqiqiy noyob kalit sifatida ishlatiladi.)
    try:
        cur.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_portfel_portkod_unique
            ON portfel(port_kod)
        ''')
    except sqlite3.IntegrityError:
        # Eski bazada takrorlangan port_kod qiymatlari bo'lsa (masalan
        # texnik "0" qatorlar) — takrorlarni tozalashdan oldin, ularga
        # bog'langan xatlar/Davo arizalarni saqlanib qoladigan (MAX id)
        # qatorga qayta yo'naltiramiz — aks holda FOREIGN KEY xatosi chiqadi.
        cur.execute('''
            UPDATE xatlar SET portfel_id = (
                SELECT MAX(p2.id) FROM portfel p2
                WHERE p2.port_kod = (SELECT p1.port_kod FROM portfel p1 WHERE p1.id = xatlar.portfel_id)
            )
            WHERE portfel_id IN (
                SELECT id FROM portfel WHERE id NOT IN (
                    SELECT MAX(id) FROM portfel GROUP BY port_kod
                )
            )
        ''')
        cur.execute('''
            DELETE FROM portfel WHERE id NOT IN (
                SELECT MAX(id) FROM portfel GROUP BY port_kod
            )
        ''')
        cur.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_portfel_portkod_unique
            ON portfel(port_kod)
        ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS mijozlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        turi TEXT,                  -- 'jismoniy' yoki 'yuridik'
        kalit TEXT,                 -- bog'lash uchun: unikal / стир / пинфл
        ism TEXT,
        manzil TEXT,
        telefon TEXT,
        hujjat_raqami TEXT,         -- pasport yoki STIR
        rahbar_ism TEXT,
        import_sanasi TEXT,
        UNIQUE(kalit, turi)
    )
    ''')

    # Eski bazalarda mavjud bo'lmasa, pasport tafsilot ustunlarini qo'shamiz
    existing_mijoz_cols = {r['name'] for r in conn.execute("PRAGMA table_info(mijozlar)").fetchall()}
    for col in ['passport_sana', 'passport_organ']:
        if col not in existing_mijoz_cols:
            cur.execute(f'ALTER TABLE mijozlar ADD COLUMN {col} TEXT')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS vafot_etganlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfel_id INTEGER,
        anketa_raqami TEXT,
        mijoz_nomi TEXT,
        vafot_sanasi TEXT,                    -- kun.oy.yil
        olimlik_guvohnomasi_fayl TEXT,
        pasport_fayl TEXT,
        kredit_tugash_sanasi TEXT,             -- portfeldan olingan (surat)
        polis_holati TEXT DEFAULT 'tekshirilmagan',  -- tekshirilmagan / amalda / muddati_otgan
        sugurta_kompaniya TEXT,
        sugurta_polis_raqam TEXT,
        sugurta_polis_fayl TEXT,
        xabarnoma_holati TEXT DEFAULT 'kerak', -- kerak / yuborildi / javob_keldi
        xabarnoma_yuborilgan_sana TEXT,
        javob_kelgan_sana TEXT,
        javob_fayl TEXT,
        yaratilgan_sana TEXT,
        FOREIGN KEY(portfel_id) REFERENCES portfel(id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS mib_avtomashinalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        xat_id INTEGER,
        mashina_rusumi TEXT,
        davlat_raqami TEXT,
        mijoz_pinfl TEXT,
        holati TEXT DEFAULT 'xatlanmagan',   -- xatlanmagan / taqiq / qidiruv / xatlangan
        asoslovchi_hujjat_fayl TEXT,
        modda TEXT,
        holat_sanasi TEXT,
        qoshilgan_sana TEXT,
        FOREIGN KEY(xat_id) REFERENCES xatlar(id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS mib_amallar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        xat_id INTEGER,
        amal_turi TEXT,              -- oylik_ish_haqqi / avto_taqiq / avto_qidiruv /
                                      -- chetga_chiqish_taqiq / majburiy_xatlov /
                                      -- sotish_togridan / sotish_auksion /
                                      -- kafil_ish / garov_xatlov / garov_sotish
        amal_sanasi TEXT,
        tavsif TEXT,
        undirilgan_summa REAL,       -- oylik ish haqqidan yoki boshqa yo'l bilan
                                      -- ushbu amal orqali undirilgan summa
        -- Majburiy xatlov uchun:
        mulk_nomi TEXT,
        mulk_soni TEXT,
        mulk_summasi REAL,
        dalolatnoma_fayl TEXT,
        -- To'g'ridan-to'g'ri sotish uchun:
        sotilgan_nomi TEXT,
        sotilgan_soni TEXT,
        sotilgan_summasi REAL,
        -- Auksion orqali sotish uchun:
        auksion_sana TEXT,
        auksion_narxi REAL,
        auksion_lot_raqami TEXT,
        auksion_rasmlar TEXT,          -- fayl yo'llari, vergul bilan ajratilgan
        yaratilgan_sana TEXT,
        FOREIGN KEY(xat_id) REFERENCES xatlar(id)
    )
    ''')

    # Eski bazalarda mavjud bo'lmasa, yangi ustunni qo'shib qo'yamiz
    existing_mib_amal_cols = {r['name'] for r in conn.execute("PRAGMA table_info(mib_amallar)").fetchall()}
    if 'undirilgan_summa' not in existing_mib_amal_cols:
        cur.execute('ALTER TABLE mib_amallar ADD COLUMN undirilgan_summa REAL')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS davo_taminot (
        anketa_raqami TEXT PRIMARY KEY,
        taminot_turi TEXT,           -- 'yoq' / 'kafillik' / 'garov' / 'kafillik_garov'
        kafil_ism TEXT,
        kafil_manzil TEXT,
        kafil_pinfl TEXT,
        kafil_passport TEXT,
        kafil_passport_sana TEXT,
        kafil_passport_organ TEXT,
        kafil_tel TEXT,
        garov_tavsifi TEXT,          -- masalan: avtomobil rusumi, dvigatel/kuzov raqami va h.k.
        garov_bahosi REAL,
        pochta_xarajati REAL,
        yangilangan_sana TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS xatlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfel_id INTEGER,
        anketa_raqami TEXT,
        mijoz_nomi TEXT,
        mijoz_turi TEXT,
        xat_turi TEXT,               -- 'Ogohlantirish' / 'Talabnoma'
        yaratilgan_sana TEXT,
        muddat_sana TEXT,
        holat TEXT DEFAULT 'tayyor', -- tayyor / yuborildi / muddati_otgan
        yuborilgan_sana TEXT,
        fayl_yoli TEXT,
        davo_ariza_sana TEXT,
        davo_ariza_fayl_yoli TEXT,
        davo_ariza_holati TEXT,          -- 'tayyor' / 'olib_kelindi'
        davo_ariza_turi TEXT,            -- jismoniy_oddiy / yuridik_kafil va h.k.
        davo_ariza_ish_raqami TEXT,
        davo_ariza_imzo_sana TEXT,       -- imzodan/Palatadan chiqqan sana
        davo_summasi_asosiy REAL,        -- Davo ariza yaratilgan paytdagi asosiy qarz (surat)
        davo_summasi_foiz REAL,          -- Davo ariza yaratilgan paytdagi foiz qarz (surat)
        davo_summasi_jarima REAL,        -- Davo ariza yaratilgan paytdagi jarima (surat)
        qoshimcha_davo_kerak INTEGER DEFAULT 0,  -- 1 = qarz 1 BXMdan ko'p oshgan, qo'shimcha ariza kerak
        sud_holati TEXT,                 -- 'topshirilmagan' / 'topshirildi'
        sud_ish_raqami TEXT,
        sud_topshirilgan_sana TEXT,      -- sudga hujjat topshirilgan sana
        sud_buyrugi_fayl TEXT,           -- sud buyrug'i (qarori) PDF fayl yo'li
        mib_holati TEXT,                 -- 'otkazilmagan' / 'otkazildi'
        mib_ish_raqami TEXT,
        mib_otkazilgan_sana TEXT,        -- MIBga hujjat o'tkazilgan sana
        ijro_varaqasi_fayl TEXT,         -- ijro varaqasi PDF fayl yo'li
        mib_ijro_summasi REAL,           -- MIBga o'tkazilgan paytdagi qarz summasi (surat)
        yigma_jild_papka TEXT,           -- ish uchun ochilgan yig'ma jild papkasi yo'li
        sud_kiritilmadi_sababi TEXT,     -- 'qarz_yopilgan' | 'mijoz_arizasi' | 'xodim_iltimosi'
        sud_kiritilmadi_pdf TEXT,        -- mijozning yozma arizasi skani (agar shu sabab tanlansa)
        sud_kiritilmadi_xodim_ism TEXT,  -- bank xodimi F.I.Sh (agar 'xodim_iltimosi' tanlansa)
        sud_kiritilmadi_izoh TEXT,       -- qoldirish sababi tavsifi (xodim iltimosi uchun)
        sud_kiritilmadi_sana TEXT,       -- qachon qayd qilingani
        yigma_jild_titul_fayl TEXT,      -- yig'ma jild titul (muqova) hujjati yo'li
        yigma_jild_holati TEXT,          -- 'mavjud' — titul yaratilgach belgilanadi
        mib_yakunlangan INTEGER DEFAULT 0,  -- 1 = ijro ishi to'xtatilgan/yakunlangan
        mib_yakunlangan_sana TEXT,
        mib_yakunlash_sababi TEXT,
        mib_yakunlash_hujjati_fayl TEXT,
        -- Sud harakatlari yig'ma jildi (MIBdagi kabi, lekin sudgacha bo'lgan hujjatlar uchun)
        sud_yigma_jild_papka TEXT,
        sud_yigma_jild_titul_fayl TEXT,
        sud_malumotnoma_topshirishda_fayl TEXT,  -- sudga topshirishdagi qarzdorlik malumotnomasi
        sud_malumotnoma_kun_fayl TEXT,           -- sud kuni uchun (1 kun oldin) malumotnoma
        kredit_shartnoma_fayl TEXT,
        kafillik_shartnoma_fayl TEXT,
        garov_shartnoma_fayl TEXT,
        bank_baholash_fayl TEXT,
        sud_hujjatlar_ruxsat INTEGER DEFAULT 0,  -- 1 = barcha kerakli hujjatlar yuklanib, sudga yuborishga ruxsat berilgan
        -- Sud qarori (5/15 kun ichida yuklanishi kerak)
        sud_qaror_fayl TEXT,
        sud_qaror_natija TEXT,           -- 'bank_foydasiga' | 'qisman' | 'rad_etildi'
        sud_qaror_sana TEXT,
        sud_qisman_asosiy_farq REAL,
        sud_qisman_foiz_farq REAL,
        sud_qisman_penya_farq REAL,
        sud_qisman_davlat_boji_sherik INTEGER DEFAULT 0,
        sud_rad_sababi TEXT,
        arxivlangan INTEGER DEFAULT 0,
        FOREIGN KEY(portfel_id) REFERENCES portfel(id)
    )
    ''')

    # Eski bazalarda mavjud bo'lmasa, yangi ustunlarni qo'shib qo'yamiz
    existing_cols = {r['name'] for r in conn.execute("PRAGMA table_info(xatlar)").fetchall()}
    for col in ['davo_ariza_sana', 'davo_ariza_fayl_yoli', 'davo_ariza_holati',
                'davo_ariza_turi', 'davo_ariza_ish_raqami', 'davo_ariza_imzo_sana',
                'davo_summasi_asosiy', 'davo_summasi_foiz', 'davo_summasi_jarima', 'qoshimcha_davo_kerak',
                'sud_holati', 'sud_ish_raqami', 'sud_topshirilgan_sana', 'sud_buyrugi_fayl',
                'mib_holati', 'mib_ish_raqami', 'mib_otkazilgan_sana', 'ijro_varaqasi_fayl',
                'yigma_jild_papka', 'yigma_jild_titul_fayl', 'yigma_jild_holati', 'mib_ijro_summasi',
                'mib_yakunlangan_sana', 'mib_yakunlash_sababi', 'mib_yakunlash_hujjati_fayl',
                'sud_kiritilmadi_sababi', 'sud_kiritilmadi_pdf', 'sud_kiritilmadi_xodim_ism',
                'sud_kiritilmadi_izoh', 'sud_kiritilmadi_sana',
                'sud_yigma_jild_papka', 'sud_yigma_jild_titul_fayl',
                'sud_malumotnoma_topshirishda_fayl', 'sud_malumotnoma_kun_fayl',
                'kredit_shartnoma_fayl', 'kafillik_shartnoma_fayl', 'garov_shartnoma_fayl', 'bank_baholash_fayl',
                'sud_qaror_fayl', 'sud_qaror_natija', 'sud_qaror_sana',
                'sud_qisman_asosiy_farq', 'sud_qisman_foiz_farq', 'sud_qisman_penya_farq',
                'sud_rad_sababi']:
        if col not in existing_cols:
            cur.execute(f'ALTER TABLE xatlar ADD COLUMN {col} TEXT')
    if 'mib_yakunlangan' not in existing_cols:
        cur.execute('ALTER TABLE xatlar ADD COLUMN mib_yakunlangan INTEGER DEFAULT 0')
    if 'sud_hujjatlar_ruxsat' not in existing_cols:
        cur.execute('ALTER TABLE xatlar ADD COLUMN sud_hujjatlar_ruxsat INTEGER DEFAULT 0')
    if 'sud_qisman_davlat_boji_sherik' not in existing_cols:
        cur.execute('ALTER TABLE xatlar ADD COLUMN sud_qisman_davlat_boji_sherik INTEGER DEFAULT 0')
    if 'arxivlangan' not in existing_cols:
        cur.execute('ALTER TABLE xatlar ADD COLUMN arxivlangan INTEGER DEFAULT 0')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS sud_kunlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anketa_raqami TEXT,
        mijoz_nomi TEXT,
        sud_sanasi TEXT,        -- kun.oy.yil
        sud_vaqti TEXT,         -- soat:daqiqa
        sud_nomi TEXT,          -- qaysi sud (masalan "Toshkent shahar fuqarolik sudi")
        sud_ish_raqami TEXT,
        eslatma_1kun_berildi INTEGER DEFAULT 0,
        eslatma_kuni_berildi INTEGER DEFAULT 0,
        yaratilgan_sana TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS sud_xarajatlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        xat_id INTEGER,
        anketa_raqami TEXT,
        mijoz_nomi TEXT,
        pinfl_yoki_stir TEXT,
        summa REAL,
        holati TEXT DEFAULT 'kutilmoqda',  -- 'kutilmoqda' | 'mib_ochildi' | 'yakunlangan'
        mib_ijro_ish_raqami TEXT,
        yaratilgan_sana TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS kredit_hujjatlar_arxiv (
        anketa_raqami TEXT PRIMARY KEY,
        kredit_shartnoma_fayl TEXT,
        kafillik_shartnoma_fayl TEXT,
        garov_shartnoma_fayl TEXT,
        bank_baholash_fayl TEXT,
        yangilangan_sana TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS sud_qoshimcha_hujjatlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        xat_id INTEGER,
        hujjat_nomi TEXT,
        fayl_yoli TEXT,
        yuklangan_sana TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS f95413_hujjatlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anketa_raqami TEXT,
        hujjat_nomi TEXT,
        fayl_yoli TEXT,
        yuklangan_sana TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS f95413_titul (
        anketa_raqami TEXT PRIMARY KEY,
        titul_fayl TEXT,
        yaratilgan_sana TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS mib_harakat_turlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nomi TEXT UNIQUE,
        faol INTEGER DEFAULT 1
    )
    ''')

    # tolovlar jadvali eski bazada mavjud bo'lsa, tranzaksiya_raqami ustunini qo'shamiz
    try:
        tolovlar_cols = {r['name'] for r in conn.execute("PRAGMA table_info(tolovlar)").fetchall()}
        if tolovlar_cols and 'tranzaksiya_raqami' not in tolovlar_cols:
            cur.execute('ALTER TABLE tolovlar ADD COLUMN tranzaksiya_raqami TEXT')
    except Exception:
        pass

    cur.execute('''
    CREATE TABLE IF NOT EXISTS sozlamalar (
        kalit TEXT PRIMARY KEY,
        qiymat TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS foydalanuvchilar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE NOT NULL,
        parol_hash TEXT NOT NULL,
        toliq_ism TEXT,
        rol TEXT DEFAULT 'xodim',   -- 'admin' | 'xodim'
        faol INTEGER DEFAULT 1,
        yaratilgan_sana TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS tolovlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manba TEXT,                  -- 'kunlik_29801' | 'mib'
        sana TEXT,                   -- tolov sanasi (fayldan)
        summa REAL,
        pinfl_yoki_stir TEXT,
        toliq_ism TEXT,              -- fayldagi F.I.Sh/nomi (agar mavjud bo'lsa)
        anketa_raqami TEXT,          -- biriktirilgan anketa (aniqlangach to'ldiriladi)
        mijoz_nomi TEXT,             -- biriktirilgan mijoz nomi (ko'rsatish uchun)
        holati TEXT DEFAULT 'yangi', -- 'yangi' | 'aniqlash_kerak' | 'tasdiqlangan' | 'mos_kelmadi'
        izoh TEXT,
        yuklangan_sana TEXT,
        tranzaksiya_raqami TEXT       -- bank tranzaksiya raqami (dublikat aniqlash uchun)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS tahlil_tarixi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sana TEXT,                    -- portfel yangilangan sana (ISO)
        jami_soni INTEGER, jami_ead REAL,
        jismoniy_soni INTEGER, jismoniy_ead REAL,
        yuridik_soni INTEGER, yuridik_ead REAL,
        stage1_soni INTEGER, stage1_ead REAL,
        stage2_soni INTEGER, stage2_ead REAL,
        stage3_soni INTEGER, stage3_ead REAL
    )
    ''')

    defaults = {
        'bank_nomi': '"AGROBANK" ATB',
        'bank_qisqa_nomi': 'AGROBANK',
        'bank_manzil': "100096, O'zbekiston Respublikasi, Toshkent sh., Muqimiy ko'chasi, 43",
        'bank_email': 'headoffice@agrobank.uz',
        'bank_sayt': 'www.agrobank.uz',
        'bank_tel': '1216',
        'bank_mobil_ilova': 'AGROBANK',
        'bank_kodi': '00382',
        'aloqa_markazi_tel': '1216',
        'filial_nomi': 'Boyovut',
        'filial_tel': '71-202-80-08 (382-01)',
        'rahbar_ism': '',
        'tolov_muddati_kun': '10',
        'eslatma_muddati_kun': '3',
        'davo_ariza_muddati_kun': '5',
        'sud_topshirish_muddati_kun': '5',
        'mib_harakatsizlik_muddati_kun': '15',
        'bxm_miqdori': '375000',
        'mib_toxtatish_dpd_chegara': '30',
        'sugurta_javob_muddati_ish_kun': '40',
        'chora_ogohlantirish_dpd_kun': '50',
        'chora_ogohlantirish_oy': '2',
        'chora_davo_ariza_dpd_kun': '60',
        'chora_davo_ariza_oy': '1',
        'dpd_chegara_kun': '45',
        'minimal_qarz_summa': '0',

        # --- Davo ariza uchun qo'shimcha sozlamalar ---
        'bank_stir': '207243390',
        'bank_hisob_raqami_filial': '16103000700000382001',
        'bank_kodi_filial': '00382',
        'bank_hisob_raqami_bosh': '16103000200001140001',
        'bank_kodi_bosh': '01140',
        'bank_rasmiy_manzil_filial': "Sirdaryo viloyati, Boyovut tumani, Boyovut shaharchasi, Tinchlik ko'chasi, 10-uy",
        'sud_fuqarolik_nomi': 'Boyovut tumanlararo sudi',
        'sud_iqtisodiy_nomi': 'Guliston tumanlararo iqtisodiy sudi',
        'palata_nomi': "O'zbekiston Savdo-sanoat palatasi Sirdaryo viloyati hududiy boshqarmasi",
        'palata_manzil': "Сирдарё вилояти, Гулистон ш. 4-мавзе, Бўстон МФЙ, Дўстлик канали қирғоқ бўйи, "
                          "Тадбиркор ва ҳунармандлар маркази, тел. +99867 236 37 27, 1094, "
                          "e-mail: sr@chamber.uz, www.chamber.uz",
        'pochta_xarajati_standart': '41200',
        'sud_ariza_imzo_ism': '',
        'sud_ariza_imzo_lavozimi': "Бошқарма бошлиғи ўринбосари",
        'viloyat_nomi': 'Sirdaryo',
    }
    for k, v in defaults.items():
        cur.execute('INSERT OR IGNORE INTO sozlamalar (kalit, qiymat) VALUES (?, ?)', (k, v))

    conn.commit()
    conn.close()


def get_setting(kalit, default=''):
    conn = get_conn()
    row = conn.execute('SELECT qiymat FROM sozlamalar WHERE kalit=?', (kalit,)).fetchone()
    conn.close()
    return row['qiymat'] if row else default


def _parol_hash(parol):
    return hashlib.sha256(('QNT_' + parol).encode('utf-8')).hexdigest()


def parol_ornatilganmi():
    """Tizimga kirish paroli o'rnatilgan-o'rnatilmaganini tekshiradi."""
    return bool(get_setting('login_parol_hash', ''))


def parol_tekshirish(parol):
    """Kiritilgan parol saqlangan xesh bilan mos kelishini tekshiradi."""
    saqlangan = get_setting('login_parol_hash', '')
    if not saqlangan:
        return True
    return _parol_hash(parol) == saqlangan


def foydalanuvchi_yaratish(login, parol, toliq_ism='', rol='xodim'):
    """Yangi foydalanuvchi (kompyuter/xodim) hisobini yaratadi — bir nechta
    kompyuterdan bitta umumiy serverga ulanib ishlash uchun, har biriga
    alohida login/parol berish imkonini beradi."""
    conn = get_conn()
    try:
        conn.execute('''
            INSERT INTO foydalanuvchilar (login, parol_hash, toliq_ism, rol, yaratilgan_sana)
            VALUES (?, ?, ?, ?, ?)
        ''', (login.strip(), _parol_hash(parol), toliq_ism, rol, datetime.datetime.now().isoformat()))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    return ok


def foydalanuvchi_login_tekshirish(login, parol):
    """Login+parol to'g'riligini tekshiradi. To'g'ri bo'lsa, foydalanuvchi
    ma'lumotini (parolsiz) qaytaradi, aks holda None."""
    conn = get_conn()
    row = conn.execute(
        'SELECT * FROM foydalanuvchilar WHERE login=? AND faol=1', (login.strip(),)
    ).fetchone()
    conn.close()
    if row and row['parol_hash'] == _parol_hash(parol):
        return {'id': row['id'], 'login': row['login'], 'toliq_ism': row['toliq_ism'], 'rol': row['rol']}
    return None


def foydalanuvchilar_royxati():
    conn = get_conn()
    rows = conn.execute('SELECT id, login, toliq_ism, rol, faol, yaratilgan_sana FROM foydalanuvchilar ORDER BY id').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def foydalanuvchi_ochirish(user_id):
    conn = get_conn()
    conn.execute('DELETE FROM foydalanuvchilar WHERE id=?', (user_id,))
    conn.commit()
    conn.close()


def foydalanuvchi_faollik(user_id, faol):
    conn = get_conn()
    conn.execute('UPDATE foydalanuvchilar SET faol=? WHERE id=?', (1 if faol else 0, user_id))
    conn.commit()
    conn.close()


def foydalanuvchilar_bormi():
    conn = get_conn()
    soni = conn.execute('SELECT COUNT(*) c FROM foydalanuvchilar').fetchone()['c']
    conn.close()
    return soni > 0


def parol_ornatish(yangi_parol):
    """Yangi kirish parolini (xesh holida) saqlaydi. Bo'sh qator berilsa,
    parol talabi butunlay o'chiriladi (kirish erkin bo'ladi)."""
    if yangi_parol:
        set_setting('login_parol_hash', _parol_hash(yangi_parol))
    else:
        set_setting('login_parol_hash', '')


def get_all_settings():
    conn = get_conn()
    rows = conn.execute('SELECT kalit, qiymat FROM sozlamalar').fetchall()
    conn.close()
    return {r['kalit']: r['qiymat'] for r in rows}


def set_setting(kalit, qiymat):
    conn = get_conn()
    conn.execute('INSERT INTO sozlamalar (kalit, qiymat) VALUES (?, ?) '
                 'ON CONFLICT(kalit) DO UPDATE SET qiymat=excluded.qiymat', (kalit, qiymat))
    conn.commit()
    conn.close()


def clear_portfel():
    conn = get_conn()
    conn.execute('DELETE FROM portfel')
    conn.commit()
    conn.close()


def insert_portfel_rows(rows):
    """
    rows: list of dicts matching portfel columns (without id).
    Anketa raqami bo'yicha UPSERT qiladi — mavjud kredit yangilanadi,
    yangi kredit qo'shiladi. Portfel ID'lari saqlanib qoladi, shunda
    ularga bog'liq xatlar/Davo arizalar bog'lanishi buzilmaydi.

    MUHIM: yangi faylda endi UCHRAMAGAN (masalan to'langan yoki bank
    tomonidan chiqarib tashlangan) kreditlar bazadan o'CHIRILMAYDI —
    ularga bog'liq xat/Davo ariza/Sud/MIB tarixi yo'qolib qolmasligi
    uchun. Buning o'rniga ular "faol=0" deb belgilanadi va Tahlil,
    Chora ko'rish, 95413 kabi JORIY holatni ko'rsatuvchi bo'limlardan
    avtomatik chiqarib tashlanadi — shu bilan eski (allaqachon yopilgan)
    kreditlar statistikaga qo'shilib, sonlarni sun'iy oshirib yubormaydi.
    """
    conn = get_conn()
    cur = conn.cursor()
    cols = ['port_kod', 'anketa_raqami', 'unikal', 'stir', 'pinfl', 'filial_kodi', 'viloyat',
            'tarmoq', 'stage',
            'mijoz_turi_kodi', 'mijoz_turi', 'mijoz_nomi', 'valyuta', 'kredit_hisob_raqami',
            'yillik_foiz', 'shartnoma_sanasi', 'shartnoma_tugash_sanasi', 'tulov_maqsadi',
            'dpd_asosiy', 'dpd_foiz', 'dpd_max', 'ead', 'jami_qarz', 'asosiy_qarz', 'foiz_qarz',
            'jarima', 'balans_95413', 'import_sanasi', 'holat']
    placeholders = ','.join(['?'] * len(cols))
    update_cols = [c for c in cols if c not in ('port_kod',)]
    set_clause = ', '.join(f'{c}=excluded.{c}' for c in update_cols) + ', faol=1'
    sql = f'''INSERT INTO portfel ({','.join(cols)}) VALUES ({placeholders})
              ON CONFLICT(port_kod) DO UPDATE SET {set_clause}'''
    now = datetime.datetime.now().isoformat()
    for r in rows:
        r.setdefault('import_sanasi', now)
        r.setdefault('holat', 'yangi')
        values = [r.get(c) for c in cols]
        cur.execute(sql, values)

    # Shu importda "yangilanmagan" (import_sanasi hali eski qolgan) barcha
    # qatorlarni "faol emas" deb belgilaymiz — ular yangi faylda umuman
    # uchramagan, demak endi joriy portfelning bir qismi emas.
    cur.execute('UPDATE portfel SET faol=0 WHERE import_sanasi < ?', (now,))

    conn.commit()
    conn.close()


def upsert_mijoz(turi, kalit, ism, manzil, telefon, hujjat_raqami, rahbar_ism='',
                  passport_sana='', passport_organ=''):
    conn = get_conn()
    now = datetime.datetime.now().isoformat()
    conn.execute('''
        INSERT INTO mijozlar (turi, kalit, ism, manzil, telefon, hujjat_raqami, rahbar_ism,
                               passport_sana, passport_organ, import_sanasi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(kalit, turi) DO UPDATE SET
            ism=excluded.ism, manzil=excluded.manzil, telefon=excluded.telefon,
            hujjat_raqami=excluded.hujjat_raqami, rahbar_ism=excluded.rahbar_ism,
            passport_sana=excluded.passport_sana, passport_organ=excluded.passport_organ,
            import_sanasi=excluded.import_sanasi
    ''', (turi, kalit, ism, manzil, telefon, hujjat_raqami, rahbar_ism,
          passport_sana, passport_organ, now))
    conn.commit()
    conn.close()


def bulk_upsert_mijozlar(records):
    """
    records: list of tuples (turi, kalit, ism, manzil, telefon, hujjat_raqami, rahbar_ism,
                              passport_sana, passport_organ)
    Bitta ulanish/tranzaksiya orqali ko'p mijozni tez saqlaydi.
    """
    conn = get_conn()
    now = datetime.datetime.now().isoformat()
    conn.executemany('''
        INSERT INTO mijozlar (turi, kalit, ism, manzil, telefon, hujjat_raqami, rahbar_ism,
                               passport_sana, passport_organ, import_sanasi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(kalit, turi) DO UPDATE SET
            ism=excluded.ism, manzil=excluded.manzil, telefon=excluded.telefon,
            hujjat_raqami=excluded.hujjat_raqami, rahbar_ism=excluded.rahbar_ism,
            passport_sana=excluded.passport_sana, passport_organ=excluded.passport_organ,
            import_sanasi=excluded.import_sanasi
    ''', [(t, k, i, m, tel, h, r, ps, po, now) for (t, k, i, m, tel, h, r, ps, po) in records])
    conn.commit()
    conn.close()


def find_mijoz(turi, kalit):
    conn = get_conn()
    row = conn.execute('SELECT * FROM mijozlar WHERE turi=? AND kalit=?', (turi, kalit)).fetchone()
    conn.close()
    return dict(row) if row else None


def matndan_pinfl_yoki_stir_ajratish(matn):
    """Erkin matndan (hisob raqami, to'lov maqsadi/naznacheniye va h.k.)
    PINFL (14 ta ketma-ket raqam) yoki STIR (9 ta ketma-ket raqam)ga o'xshash
    qismlarni qidirib topadi. Avval PINFL (aniqroq, uzunroq) qidiriladi.
    Topilgan barcha nomzodlarni ro'yxat qilib qaytaradi (tartib bo'yicha)."""
    if not matn:
        return []
    matn = str(matn)
    nomzodlar = []
    for m in re.finditer(r'\d{14}', matn):
        nomzodlar.append(m.group())
    if not nomzodlar:
        for m in re.finditer(r'\d{9}', matn):
            nomzodlar.append(m.group())
    return nomzodlar


def tolov_unikal_orqali_topish(hisob_raqami):
    """Kunlik (29801-hisobvaraq) to'lovlar uchun: to'liq hisob raqami
    ICHIDA portfeldagi 'unikal' (mijozning o'ziga xos, uzunligi
    o'zgaruvchan kodi) qidiriladi. Masalan hisob raqami
    '298010009643446135001' bo'lsa va biror mijozning unikal kodi
    '5443864' bo'lsa — bu qism hisob raqami ichida "ko'milgan" holda
    joylashadi va shu orqali topiladi."""
    if not hisob_raqami or not hisob_raqami.isdigit() or len(hisob_raqami) < 15:
        return []
    conn = get_conn()
    rows = conn.execute('''
        SELECT anketa_raqami, mijoz_nomi, asosiy_qarz, foiz_qarz, jarima, unikal
        FROM portfel
        WHERE faol=1 AND unikal IS NOT NULL AND unikal != ''
          AND length(unikal) >= 5 AND instr(?, unikal) > 0
    ''', (hisob_raqami,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def tolov_uchun_anketalarni_topish(pinfl_yoki_stir):
    """Berilgan PINFL/STIR bo'yicha portfeldagi FAOL kreditlarning barcha
    anketa raqamlarini qaytaradi. Agar bitta mijozning bir nechta krediti
    (anketasi) bo'lsa, bularning barchasi qaytariladi — shunda foydalanuvchi
    qaysi biriga to'lov tegishli ekanini tanlashi mumkin."""
    # PINFL (14 raqam) yoki STIR (9 raqam) dan qisqaroq (masalan "0" yoki
    # bo'sh, ma'lumotlar bazasida ko'plab "to'ldirilmagan" yozuv sifatida
    # uchraydigan) qiymatlarni ma'noli deb hisoblamaymiz — aks holda
    # minglab noto'g'ri "nomzod" chiqib, foydasiz bo'lib qoladi.
    if not pinfl_yoki_stir or len(pinfl_yoki_stir.strip()) < 9:
        return []
    conn = get_conn()
    rows = conn.execute('''
        SELECT anketa_raqami, mijoz_nomi, asosiy_qarz, foiz_qarz, jarima
        FROM portfel WHERE faol=1 AND (pinfl=? OR stir=?)
    ''', (pinfl_yoki_stir, pinfl_yoki_stir)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def tolov_hisob_raqami_boyicha_topish(hisob_raqami):
    """To'liq kredit hisob raqami (masalan 20 xonali) bo'yicha portfelda
    ANIQ mos keladigan yozuvni qidiradi. Bu — eng ISHONCHLI usul, chunki
    har bir kredit o'zining YAGONA hisob raqamiga ega."""
    if not hisob_raqami or len(hisob_raqami.strip()) < 10:
        return []
    conn = get_conn()
    rows = conn.execute('''
        SELECT anketa_raqami, mijoz_nomi, asosiy_qarz, foiz_qarz, jarima
        FROM portfel WHERE faol=1 AND kredit_hisob_raqami=?
    ''', (hisob_raqami.strip(),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def tolov_qoshish(manba, sana, summa, xom_matn, toliq_ism=None, tranzaksiya_raqami=None):
    """Yangi to'lov yozuvini qo'shadi va mos anketa(lar)ni, TO'LOV MANBASIGA
    qarab, mos strategiya bilan aniqlashga harakat qiladi:

    'kunlik_29801' (bank hisob raqami asosida):
      1-bosqich: 'xom_matn' to'liq kredit hisob raqami sifatida ANIQ mos
                 kelsa (eng ishonchli) — shundan foydalaniladi.
      2-bosqich: 'xom_matn' (uzun hisob raqami) ICHIDA portfeldagi
                 'unikal' kodi qidiriladi.

    'mib' (Ijro byurosidan kelgan, naznacheniye/izoh matni asosida):
      1-bosqich: matn ichidan PINFL (14 xonali) yoki STIR (9 xonali)
                 ko'rinishidagi raqam ketma-ketligi qidirib topiladi.
      2-bosqich: matnning o'zi to'g'ridan-to'g'ri PINFL/STIR bo'lishi mumkin.

    Har ikkala holatda ham: hech narsa yoki bir nechta anketa topilsa,
    tizim HECH QACHON o'zi "taxmin qilib" yakuniy tasdiqlash bermaydi —
    foydalanuvchi tasdiqlashi yoki qo'lda qidirib topishi kerak bo'ladi
    (pul noto'g'ri mijozga yozilib qolmasligi uchun).

    MUHIM (dublikat himoyasi): agar 'tranzaksiya_raqami' berilgan bo'lsa
    va bu tranzaksiya raqami bilan to'lov ALLAQACHON bazada mavjud bo'lsa
    — bu YANGI qator DUBLIKAT deb hisoblanadi va qo'shilmaydi (masalan
    xodim bir xil kunlik faylni ikki marta yuklab yuborgan bo'lsa). Bu —
    bir kunda BIR NECHTA HAQIQIY (turli tranzaksiya raqamli) to'lov bir
    xil hisob raqamiga kelishi bilan ARALASHTIRILMAYDI."""
    if tranzaksiya_raqami:
        conn = get_conn()
        mavjud = conn.execute(
            'SELECT id FROM tolovlar WHERE tranzaksiya_raqami=? AND tranzaksiya_raqami != ""',
            (tranzaksiya_raqami,)).fetchone()
        conn.close()
        if mavjud:
            return 'dublikat', None

    xom_matn = (xom_matn or '').strip()
    nomzodlar = []
    aniqlangan_id = xom_matn

    if manba == 'mib':
        ajratilganlar = matndan_pinfl_yoki_stir_ajratish(xom_matn)
        for nomzod_id in ajratilganlar:
            topilgan = tolov_uchun_anketalarni_topish(nomzod_id)
            if topilgan:
                nomzodlar = topilgan
                aniqlangan_id = nomzod_id
                break
        else:
            nomzodlar = tolov_uchun_anketalarni_topish(xom_matn)
    else:
        nomzodlar = tolov_hisob_raqami_boyicha_topish(xom_matn)
        if not nomzodlar:
            unikal_orqali = tolov_unikal_orqali_topish(xom_matn)
            if unikal_orqali:
                nomzodlar = unikal_orqali
                # MUHIM: saqlanadigan ID ham ajratib olingan 'unikal'
                # qiymatiga yangilanishi kerak — aks holda keyinchalik
                # "Anketa tanlash" oynasi to'liq hisob raqami bo'yicha
                # qidirib, hech narsa topa olmay qolar edi.
                aniqlangan_id = unikal_orqali[0].get('unikal', xom_matn)

    if len(nomzodlar) == 1:
        holati = 'tasdiqlangan'
        anketa = nomzodlar[0]['anketa_raqami']
        mijoz_nomi = nomzodlar[0]['mijoz_nomi']
    elif len(nomzodlar) > 1:
        holati = 'aniqlash_kerak'
        anketa, mijoz_nomi = None, (toliq_ism or nomzodlar[0]['mijoz_nomi'])
    else:
        holati = 'mos_kelmadi'
        anketa, mijoz_nomi = None, toliq_ism

    conn = get_conn()
    conn.execute('''
        INSERT INTO tolovlar (manba, sana, summa, pinfl_yoki_stir, toliq_ism,
            anketa_raqami, mijoz_nomi, holati, yuklangan_sana, tranzaksiya_raqami)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (manba, sana, summa, aniqlangan_id, toliq_ism, anketa, mijoz_nomi,
          holati, datetime.datetime.now().isoformat(), tranzaksiya_raqami))
    conn.commit()
    conn.close()
    return holati, anketa


def tolov_qidirib_biriktirish(qidiruv_matni):
    """Agar avtomatik aniqlash umuman ishlamasa, foydalanuvchi ANKETA
    RAQAMI yoki MIJOZ NOMI bo'yicha qo'lda qidirib, to'g'ri kreditni
    topishi uchun — bu ENG OXIRGI, xavfsiz variant."""
    if not qidiruv_matni or len(qidiruv_matni.strip()) < 2:
        return []
    q = f"%{qidiruv_matni.strip()}%"
    conn = get_conn()
    rows = conn.execute('''
        SELECT anketa_raqami, mijoz_nomi, asosiy_qarz, foiz_qarz, jarima
        FROM portfel WHERE faol=1 AND (anketa_raqami LIKE ? OR mijoz_nomi LIKE ?)
        LIMIT 20
    ''', (q, q)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def tolov_anketa_biriktirish(tolov_id, anketa_raqami):
    conn = get_conn()
    row = conn.execute('SELECT mijoz_nomi FROM portfel WHERE anketa_raqami=? AND faol=1',
                        (anketa_raqami,)).fetchone()
    mijoz_nomi = row['mijoz_nomi'] if row else None
    conn.execute('''UPDATE tolovlar SET anketa_raqami=?, mijoz_nomi=?, holati='tasdiqlangan'
                     WHERE id=?''', (anketa_raqami, mijoz_nomi, tolov_id))
    conn.commit()
    conn.close()


def tolovlar_jami_va_royxat(anketa_raqami):
    """Berilgan anketaga TASDIQLANGAN (holati='tasdiqlangan') barcha
    to'lovlarning yig'indisini va to'liq ro'yxatini qaytaradi — MIB ishini
    to'lovlar asosida avtomatik yakunlash tekshiruvi uchun kerak."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM tolovlar WHERE anketa_raqami=? AND holati='tasdiqlangan'
        ORDER BY sana ASC
    ''', (anketa_raqami,)).fetchall()
    conn.close()
    royxat = [dict(r) for r in rows]
    jami = sum(r['summa'] or 0 for r in royxat)
    return jami, royxat


def get_tolovlar_royxati(manba=None, holati=None):
    conn = get_conn()
    query = 'SELECT * FROM tolovlar WHERE 1=1'
    params = []
    if manba:
        query += ' AND manba=?'
        params.append(manba)
    if holati:
        query += ' AND holati=?'
        params.append(holati)
    query += ' ORDER BY id DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def dpd_asosida_erta_bosqich_ishlarni_tozalash():
    """Portfel har yangilanganda chaqiriladi. Agar biror mijozning ERTA
    BOSQICH ishi (xat yuborilgan, lekin hali sudga chiqarilmagan — ya'ni
    Davo ariza SSPdan tasdiqlanib qaytmagan, sudga topshirilmagan, MIBga
    o'tkazilmagan va "sudga kiritilmadi" deb ham belgilanmagan) bo'lsa-yu,
    JORIY (yangilangan) portfel bo'yicha DPD "ogohlantirish" chegarasidan
    PASTGA tushib qolgan bo'lsa (qarzdorlik holati yaxshilangan/o'zgargan
    degani) — bu ish AVTOMATIK yakunlangan (tozalangan) deb hisoblanadi:
    tegishli 'xatlar' yozuvi o'chiriladi. Shunda:
      - Bu mijoz endi Chora ko'rishda "chiqarish kerak" deb ko'rinmaydi
      - Agar keyinchalik DPD yana chegaradan oshsa, mijoz "toza sahifa"dan,
        yangi xat bilan boshlaydi (eski, endi noto'g'ri bo'lib qolgan
        holat aralashmaydi)
    Sudga chiqarilgan (sud_holati='topshirildi' yoki mib_holati='otkazildi')
    ishlarga bu funksiya HECH QACHON tegmaydi — ular alohida, huquqiy
    jarayon sifatida davom etadi.
    """
    settings = get_all_settings()
    # MUHIM: 'dpd_chegara_kun' — Sozlamalarda foydalanuvchi ko'radigan va
    # o'zgartira oladigan YAGONA DPD chegarasi. Ilgari bu yerda alohida,
    # ekranda ko'rinmaydigan 'chora_ogohlantirish_dpd_kun' ishlatilar edi
    # (foydalanuvchi Sozlamada o'zgartirsa ham ta'sir qilmasdi) — endi
    # ikkalasi BIR XIL, ko'rinadigan qiymatga bog'landi.
    dpd_ogoh = int(settings.get('dpd_chegara_kun', settings.get('chora_ogohlantirish_dpd_kun', 45)))
    conn = get_conn()
    erta_bosqich = conn.execute('''
        SELECT x.id, x.anketa_raqami, x.portfel_id FROM xatlar x
        WHERE x.holat='yuborildi'
          AND (x.sud_holati IS NULL OR x.sud_holati != 'topshirildi')
          AND (x.mib_holati IS NULL OR x.mib_holati != 'otkazildi')
          AND (x.davo_ariza_holati IS NULL OR x.davo_ariza_holati != 'olib_kelindi')
          AND (x.sud_kiritilmadi_sababi IS NULL OR x.sud_kiritilmadi_sababi = '')
          AND (x.arxivlangan IS NULL OR x.arxivlangan = 0)
    ''').fetchall()

    tozalangan_soni = 0
    for row in erta_bosqich:
        prow = conn.execute('SELECT dpd_max FROM portfel WHERE id=?', (row['portfel_id'],)).fetchone()
        joriy_dpd = prow['dpd_max'] if prow else 0
        if joriy_dpd is None or joriy_dpd < dpd_ogoh:
            conn.execute('DELETE FROM mib_amallar WHERE xat_id=?', (row['id'],))
            conn.execute('DELETE FROM xatlar WHERE id=?', (row['id'],))
            tozalangan_soni += 1
    conn.commit()
    conn.close()
    return tozalangan_soni


def tahlil_snapshot_saqlash():
    """Portfel har yangilanganda ('import_portfel_xlsb' muvaffaqiyatli
    tugagach) shu funksiya chaqiriladi va o'sha kundagi asosiy ko'rsatkichlar
    (jami, jismoniy/yuridik, Stage 1/2/3) 'tahlil_tarixi' jadvaliga
    saqlanadi — vaqt o'tishi bilan haqiqiy tendensiya grafigini chizish
    uchun. Bir kunda bir necha marta import qilinsa, o'sha kungi eng oxirgi
    holat bilan yangilanadi (bir kunga bitta yozuv)."""
    t = get_umumiy_tahlil()
    bugun = datetime.date.today().isoformat()
    stage_map = {str(s['stage']): s for s in t['stage']}
    s1 = stage_map.get('1', {'soni': 0, 'ead': 0})
    s2 = stage_map.get('2', {'soni': 0, 'ead': 0})
    s3 = stage_map.get('3', {'soni': 0, 'ead': 0})

    conn = get_conn()
    mavjud = conn.execute('SELECT id FROM tahlil_tarixi WHERE sana=?', (bugun,)).fetchone()
    if mavjud:
        conn.execute('''
            UPDATE tahlil_tarixi SET jami_soni=?, jami_ead=?, jismoniy_soni=?, jismoniy_ead=?,
                yuridik_soni=?, yuridik_ead=?, stage1_soni=?, stage1_ead=?,
                stage2_soni=?, stage2_ead=?, stage3_soni=?, stage3_ead=? WHERE sana=?
        ''', (t['jami_soni'], t['jami_ead'], t['jismoniy']['soni'], t['jismoniy']['ead'],
              t['yuridik']['soni'], t['yuridik']['ead'], s1['soni'], s1['ead'],
              s2['soni'], s2['ead'], s3['soni'], s3['ead'], bugun))
    else:
        conn.execute('''
            INSERT INTO tahlil_tarixi (sana, jami_soni, jami_ead, jismoniy_soni, jismoniy_ead,
                yuridik_soni, yuridik_ead, stage1_soni, stage1_ead, stage2_soni, stage2_ead,
                stage3_soni, stage3_ead) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (bugun, t['jami_soni'], t['jami_ead'], t['jismoniy']['soni'], t['jismoniy']['ead'],
              t['yuridik']['soni'], t['yuridik']['ead'], s1['soni'], s1['ead'],
              s2['soni'], s2['ead'], s3['soni'], s3['ead']))
    conn.commit()
    conn.close()


def get_tahlil_tarixi(oxirgi_n_kun=90):
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM tahlil_tarixi ORDER BY sana ASC LIMIT ?', (oxirgi_n_kun,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_umumiy_tahlil():
    """
    Butun portfel bo'yicha umumiy tahlil: jami mijozlar/EAD, jismoniy/yuridik
    taqsimoti, tarmoq kesimida (soni+summasi), Stage 1/2/3 taqsimoti
    (soni+summasi+ulush). "Tahlil" bo'limi uchun asosiy ma'lumot manbai.
    """
    conn = get_conn()

    umumiy = conn.execute('SELECT COUNT(*) soni, COALESCE(SUM(ead),0) ead FROM portfel WHERE faol=1').fetchone()

    turi_rows = conn.execute('''
        SELECT mijoz_turi, COUNT(*) soni, COALESCE(SUM(ead),0) ead FROM portfel WHERE faol=1 GROUP BY mijoz_turi
    ''').fetchall()
    jismoniy = {'soni': 0, 'ead': 0}
    yuridik = {'soni': 0, 'ead': 0}
    for r in turi_rows:
        turi = str(r['mijoz_turi'] or '').strip().upper()
        target = yuridik if turi == 'LE' else jismoniy
        target['soni'] += r['soni']
        target['ead'] += r['ead'] or 0

    tarmoq_rows = conn.execute('''
        SELECT COALESCE(NULLIF(TRIM(tarmoq), ''), "Noma'lum") AS tarmoq,
               COUNT(*) AS soni, COALESCE(SUM(ead),0) AS ead
        FROM portfel WHERE faol=1 GROUP BY tarmoq ORDER BY ead DESC
    ''').fetchall()

    stage_rows = conn.execute('''
        SELECT COALESCE(NULLIF(TRIM(stage), ''), "Noma'lum") AS stage,
               COUNT(*) AS soni, COALESCE(SUM(ead),0) AS ead
        FROM portfel WHERE faol=1 GROUP BY stage
    ''').fetchall()
    conn.close()

    jami_ead = umumiy['ead'] or 0
    stage_natija = []
    for r in stage_rows:
        ead = r['ead'] or 0
        stage_natija.append({
            'stage': r['stage'], 'soni': r['soni'], 'ead': ead,
            'ulush': round(ead / jami_ead * 100, 1) if jami_ead > 0 else 0,
        })
    stage_natija.sort(key=lambda x: str(x['stage']))

    return {
        'jami_soni': umumiy['soni'], 'jami_ead': jami_ead,
        'jismoniy': jismoniy, 'yuridik': yuridik,
        'tarmoq': [dict(r) for r in tarmoq_rows],
        'stage': stage_natija,
    }


def get_reja_tarmoq_kesimida():
    """
    "Reja Grafik" bo'limi uchun: bugun (va umuman) tarmoq kesimida qancha
    Ogohlantirish xati tayyorlangani/yuborilgani, Davo ariza kiritilgani,
    sudga va MIBga o'tkazilgani.
    """
    conn = get_conn()
    rows = conn.execute('''
        SELECT COALESCE(NULLIF(TRIM(p.tarmoq), ''), "Noma'lum") AS tarmoq,
               COUNT(DISTINCT x.id) AS xat_soni,
               SUM(CASE WHEN x.holat IN ('yuborildi','muddati_otgan') THEN 1 ELSE 0 END) AS yuborilgan_soni,
               SUM(CASE WHEN x.davo_ariza_fayl_yoli IS NOT NULL THEN 1 ELSE 0 END) AS davo_soni,
               SUM(CASE WHEN x.sud_holati='topshirildi' THEN 1 ELSE 0 END) AS sud_soni,
               SUM(CASE WHEN x.mib_holati='otkazildi' THEN 1 ELSE 0 END) AS mib_soni
        FROM xatlar x
        JOIN portfel p ON p.id = x.portfel_id
        GROUP BY p.tarmoq
        ORDER BY xat_soni DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tarmoq_stage3_breakdown(limit=8):
    """Tarmoq (soha) bo'yicha Stage 3 (eng muammoli) kreditlar taqsimoti."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT COALESCE(NULLIF(TRIM(tarmoq), ''), "Noma'lum") AS tarmoq,
               COUNT(*) AS soni, SUM(jami_qarz) AS jami
        FROM portfel
        WHERE TRIM(stage) = '3' AND faol=1
        GROUP BY tarmoq
        ORDER BY jami DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tarmoq_stage3_breakdown_toliq(limit=None):
    """
    Tarmoq (soha) bo'yicha Stage 3 kreditlarning TO'LIQ taqsimoti — jami
    soni/summasi, shundan qanchasi jismoniy va qanchasi yuridik shaxsga
    tegishli ekani alohida ko'rsatiladi. Bosh sahifadagi grafik ostidagi
    jadval uchun ishlatiladi.
    """
    conn = get_conn()
    rows = conn.execute('''
        SELECT COALESCE(NULLIF(TRIM(tarmoq), ''), "Noma'lum") AS tarmoq,
               COUNT(*) AS soni, COALESCE(SUM(jami_qarz), 0) AS jami,
               SUM(CASE WHEN mijoz_turi != 'LE' THEN 1 ELSE 0 END) AS jismoniy_soni,
               COALESCE(SUM(CASE WHEN mijoz_turi != 'LE' THEN jami_qarz ELSE 0 END), 0) AS jismoniy_jami,
               SUM(CASE WHEN mijoz_turi = 'LE' THEN 1 ELSE 0 END) AS yuridik_soni,
               COALESCE(SUM(CASE WHEN mijoz_turi = 'LE' THEN jami_qarz ELSE 0 END), 0) AS yuridik_jami
        FROM portfel
        WHERE TRIM(stage) = '3' AND faol=1
        GROUP BY tarmoq
        ORDER BY jami DESC
        LIMIT ?
    ''', (limit or -1,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_viloyat_breakdown(chegara_kun=45, limit=8):
    """Viloyat bo'yicha 45+ kun mijozlar soni va muddati o'tgan qarz yig'indisi."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT COALESCE(NULLIF(TRIM(viloyat), ''), "Noma'lum") AS viloyat,
               COUNT(*) AS soni, SUM(jami_qarz) AS jami
        FROM portfel
        WHERE dpd_max >= ? AND faol=1
        GROUP BY viloyat
        ORDER BY jami DESC
        LIMIT ?
    ''', (chegara_kun, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_turi_breakdown(chegara_kun=45):
    """Jismoniy/yuridik (portfeldagi 'Мижоз тури' — LE/Individual — asosida) taqsimot."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT mijoz_turi, COUNT(*) AS soni
        FROM portfel WHERE dpd_max >= ? AND faol=1
        GROUP BY mijoz_turi
    ''', (chegara_kun,)).fetchall()
    conn.close()
    jismoniy, yuridik = 0, 0
    for r in rows:
        turi = str(r['mijoz_turi'] or '').strip().upper()
        if turi == 'LE':
            yuridik += r['soni']
        else:
            jismoniy += r['soni']
    return {'jismoniy': jismoniy, 'yuridik': yuridik}


def get_bugungi_harakatlar():
    """Bugun yaratilgan va bugun yuborilgan xatlar soni (har bir anketa faqat bir marta
    hisoblanadi — agar bazada eski dublikatlar qolgan bo'lsa ham son shishmasin)."""
    bugun = datetime.date.today().isoformat()
    conn = get_conn()
    yaratildi = conn.execute(
        "SELECT COUNT(DISTINCT anketa_raqami) c FROM xatlar WHERE yaratilgan_sana LIKE ?", (bugun + '%',)
    ).fetchone()['c']
    yuborildi = conn.execute(
        "SELECT COUNT(DISTINCT anketa_raqami) c FROM xatlar WHERE yuborilgan_sana LIKE ?", (bugun + '%',)
    ).fetchone()['c']
    conn.close()
    return {'yaratildi': yaratildi, 'yuborildi': yuborildi}


def get_latest_xat_status_by_portfel():
    """Har bir portfel_id uchun eng oxirgi xat holatini qaytaradi: {portfel_id: holat}"""
    conn = get_conn()
    rows = conn.execute('''
        SELECT portfel_id, holat FROM xatlar x1
        WHERE yaratilgan_sana = (
            SELECT MAX(yaratilgan_sana) FROM xatlar x2 WHERE x2.portfel_id = x1.portfel_id
        )
    ''').fetchall()
    conn.close()
    return {r['portfel_id']: r['holat'] for r in rows}


def get_portfel_45_kun(chegara_kun=45):
    """MUHIM: 'vafot_etganlar' jadvalida qayd qilingan mijozlar bu
    ro'yxatdan CHIQARIB TASHLANADI — ular uchun alohida (sug'urta orqali)
    jarayon bor, va ular Talabnoma/Chora ko'rish kabi oddiy qarz undirish
    oqimida qatnashmasligi kerak.

    Bundan tashqari, Sozlamalarda o'rnatilgan 'minimal_qarz_summa'dan PAST
    bo'lgan (muddati o'tgan) qarzdorlikka ega mijozlar ham chiqarib
    tashlanadi — chunki kichik summalar uchun xat/Davo ariza tayyorlash
    vaqt-mehnat sarfini oqlamasligi mumkin."""
    minimal_summa = float(get_all_settings().get('minimal_qarz_summa', 0) or 0)
    conn = get_conn()
    rows = conn.execute('''
        SELECT p.* FROM portfel p
        WHERE p.dpd_max >= ? AND p.faol=1
          AND p.anketa_raqami NOT IN (SELECT anketa_raqami FROM vafot_etganlar)
          AND (COALESCE(p.asosiy_qarz, 0) + COALESCE(p.foiz_qarz, 0) + COALESCE(p.jarima, 0)) >= ?
        ORDER BY p.dpd_max DESC
    ''', (chegara_kun, minimal_summa)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_portfel_by_id(portfel_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM portfel WHERE id=?', (portfel_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def set_jami_berilgan_summa(portfel_id, summa):
    """
    Kredit BOSHIDA berilgan asl summani (jami_berilgan_summa) saqlaydi.
    Bank eksport faylida bu ma'lumot yo'q (faqat joriy qoldiq — EAD bor),
    shu sabab bank xodimi buni bir marta qo'lda kiritadi (Excel orqali
    tahrirlab yuklash yo'li bilan), tizim esa shu qiymatni ESLAB QOLADI —
    keyingi portfel importlarida bu ustunga tegilmaydi.
    """
    conn = get_conn()
    conn.execute('UPDATE portfel SET jami_berilgan_summa=? WHERE id=?', (summa, portfel_id))
    conn.commit()
    conn.close()


def get_portfel_by_anketa(anketa_raqami):
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM portfel WHERE anketa_raqami LIKE ?', (f'%{anketa_raqami}%',)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def xat_qayta_yuborish_mumkinmi(anketa_raqami):
    """Bitta anketaga faqat BITTA xat yaratilishi kerak — LEKIN, agar
    oldingi xat allaqachon YUBORILGAN bo'lsa-yu, qarzdorlik hali
    YOPILMAGAN bo'lsa, quyidagi 2 xil holatga qarab YANGI xat (joriy
    summa bilan) yaratishga RUXSAT BERILADI (avtomatik EMAS — faqat
    ruxsat, xodim o'zi qo'lda "Xat yaratish" bosishi kerak):

      1) Agar shu vaqtgacha HECH QANDAY CHORA ko'rilmagan bo'lsa (Davo
         ariza tayyorlanmagan) — to'lov muddati (bank ish kunida)
         o'tgach, DARHOL ruxsat beriladi (jarayon "qolib ketmasin").
      2) Agar CHORA KO'RILGAN bo'lsa (Davo ariza tayyorlangan, sudga
         yoki MIBga o'tkazilgan) — bu holda yangi xat FAQAT xat
         yuborilgan kundan boshlab 60 KALENDAR KUN o'tgandan keyin
         kerak bo'ladi (chunki jarayon allaqachon davom etmoqda,
         erta xat qayta yuborish shart emas)."""
    conn = get_conn()
    eng_songgi = conn.execute(
        'SELECT * FROM xatlar WHERE anketa_raqami=? AND (arxivlangan IS NULL OR arxivlangan=0) '
        'ORDER BY id DESC LIMIT 1', (anketa_raqami,)
    ).fetchone()
    conn.close()
    if not eng_songgi:
        return True  # hali FAOL xat yo'q (yo'q, yoki barchasi arxivlangan) — yaratish mumkin
    xat = dict(eng_songgi)

    # MUHIM (tuzatildi): agar eng so'nggi sikl Davo ariza SSPdan
    # ALLAQACHON OLIB KELINGAN, lekin hali sudga TOPSHIRILMAGAN bo'lsa —
    # bu, "sudga topshirilishni kutayotgan, harakat talab qiladigan tayyor
    # ish" degani, va bu holda YANGI xat/sikl HECH QACHON yaratilishi
    # mumkin emas (kun sonidan qat'i nazar) — chunki to'g'ri amal shu
    # tayyor ishni sudga topshirish, jarayonni noldan boshlash emas.
    # (Bu tekshiruv bo'lmasa, bitta anketa uchun IKKITA parallel yozuv
    # paydo bo'lib, "Yig'ma jild/Ruxsat" holati amaliyotda yo'qolgandek
    # ko'rinib qolardi.)
    if xat.get('davo_ariza_holati') == 'olib_kelindi' and xat.get('sud_holati') != 'topshirildi':
        return False

    if xat.get('holat') != 'yuborildi' or not xat.get('yuborilgan_sana'):
        return False  # hali yuborilmagan/tayyor holatda — takror yaratish shart emas

    settings = get_all_settings()
    try:
        yuborilgan_dt = datetime.datetime.fromisoformat(xat['yuborilgan_sana'])
    except Exception:
        return False

    chora_korilganmi = bool(xat.get('davo_ariza_fayl_yoli'))
    if chora_korilganmi:
        # Chora ko'rilgan (Davo ariza/Sud/MIB) — 60 KALENDAR kun kerak
        otgan_kun = (datetime.datetime.now() - yuborilgan_dt).days
        return otgan_kun >= 60
    else:
        # Hech qanday chora ko'rilmagan — faqat to'lov muddati (bank ish
        # kunida) o'tishi kifoya
        tolov_muddati_kun = int(settings.get('tolov_muddati_kun', 10))
        otgan_ish_kunlari = _ish_kunlari_orasida(yuborilgan_dt, datetime.datetime.now())
        return otgan_ish_kunlari >= tolov_muddati_kun


def xat_qayta_yuborish_eslatmalari():
    """Muddati o'tgan, LEKIN hech qanday chora ko'rilmagan (Davo ariza
    tayyorlanmagan) xatlar ro'yxatini qaytaradi — bular uchun yangi xat
    tayyorlab yuborish TAVSIYA etiladi (avtomatik yaratilmaydi, faqat
    eslatiladi)."""
    settings = get_all_settings()
    tolov_muddati_kun = int(settings.get('tolov_muddati_kun', 10))
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar
        WHERE holat='yuborildi' AND yuborilgan_sana IS NOT NULL
          AND (davo_ariza_fayl_yoli IS NULL OR davo_ariza_fayl_yoli = '')
    ''').fetchall()
    conn.close()
    natija = []
    for row in rows:
        xat = dict(row)
        try:
            yuborilgan_dt = datetime.datetime.fromisoformat(xat['yuborilgan_sana'])
        except Exception:
            continue
        otgan_ish_kunlari = _ish_kunlari_orasida(yuborilgan_dt, datetime.datetime.now())
        if otgan_ish_kunlari >= tolov_muddati_kun:
            natija.append({
                'anketa_raqami': xat['anketa_raqami'], 'mijoz_nomi': xat['mijoz_nomi'],
                'yuborilgan_sana': xat['yuborilgan_sana'][:10],
                'otgan_ish_kunlari': otgan_ish_kunlari,
            })
    return natija


def xat_mavjudmi(anketa_raqami):
    """
    Berilgan anketa raqami uchun bazada allaqachon (istalgan holatdagi)
    FAOL (arxivlanmagan) xat yozuvi bor-yo'qligini tekshiradi. Bitta
    anketaga faqat bitta FAOL xat yaratilishi kerak — takroriy
    yaratishning oldini olish uchun ishlatiladi. Arxivlangan (eski,
    nollashtirilgan) sikllar bu tekshiruvga to'sqinlik qilmaydi.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM xatlar WHERE anketa_raqami=? AND (arxivlangan IS NULL OR arxivlangan=0) LIMIT 1",
        (anketa_raqami,)).fetchone()
    conn.close()
    return row is not None


def create_xat(portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, xat_turi, fayl_yoli, muddat_kun=3):
    conn = get_conn()
    now = datetime.datetime.now()
    muddat = now + datetime.timedelta(days=muddat_kun)
    conn.execute('''
        INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, xat_turi,
                             yaratilgan_sana, muddat_sana, holat, fayl_yoli)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'tayyor', ?)
    ''', (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, xat_turi,
          now.isoformat(), muddat.isoformat(), fayl_yoli))
    conn.commit()
    conn.close()


def get_duplicate_xat_anketalar():
    """
    Bitta anketa raqamiga bir nechta xat yozuvi yaratilgan holatlarni topadi
    (odatda ommaviy generatsiya bir necha marta takrorlanganda yuzaga keladi).
    """
    conn = get_conn()
    rows = conn.execute('''
        SELECT anketa_raqami, COUNT(*) soni FROM xatlar
        GROUP BY anketa_raqami HAVING COUNT(*) > 1
        ORDER BY soni DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def tozala_duplikat_xatlar():
    """
    Har bir dublikat anketa uchun ENG YAXSHI holatdagi bitta yozuvni saqlab
    qoladi (ustuvorlik: yuborildi > tayyor/muddati_otgan; teng bo'lsa —
    eng eskisi), qolganlarini o'chiradi. "Yuborildi" holatidagi yozuvlar hech
    qachon o'chirilmaydi (agar bir nechta "yuborildi" bo'lsa, faqat eng
    birinchisi qoladi, qolganlari — agar Davo ariza/Sud/MIBga ulanmagan
    bo'lsa — o'chiriladi).
    """
    dup = get_duplicate_xat_anketalar()
    jami_ochirildi = 0
    conn = get_conn()
    for d in dup:
        rows = conn.execute(
            'SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY yaratilgan_sana ASC',
            (d['anketa_raqami'],)
        ).fetchall()
        rows = [dict(r) for r in rows]

        def ustuvorlik(r):
            # Davo ariza/Sud/MIBga bog'langan yozuv eng qimmatli — uni saqlab qolamiz
            if r.get('mib_holati') == 'otkazildi':
                return 4
            if r.get('sud_holati') == 'topshirildi':
                return 3
            if r.get('davo_ariza_fayl_yoli'):
                return 2
            if r.get('holat') == 'yuborildi':
                return 1
            return 0

        rows.sort(key=ustuvorlik, reverse=True)
        saqlanadigan = rows[0]
        for r in rows[1:]:
            conn.execute('DELETE FROM xatlar WHERE id=?', (r['id'],))
            jami_ochirildi += 1
    conn.commit()
    conn.close()
    return jami_ochirildi


def get_xatlar(holat=None):
    conn = get_conn()
    if holat:
        rows = conn.execute('SELECT * FROM xatlar WHERE holat=? ORDER BY yaratilgan_sana DESC', (holat,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM xatlar ORDER BY yaratilgan_sana DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_xat_yuborildi(xat_id):
    conn = get_conn()
    now = datetime.datetime.now().isoformat()
    conn.execute("UPDATE xatlar SET holat='yuborildi', yuborilgan_sana=? WHERE id=?", (now, xat_id))
    conn.commit()
    conn.close()


def delete_xatlar(xat_ids):
    """
    Berilgan ID'lardagi xat yozuvlarini bazadan butunlay o'chiradi. Faqat
    hali "Yuborildi" deb belgilanmagan (davo ariza/sud/MIB bosqichiga
    o'tmagan) yozuvlarni o'chirish tavsiya etiladi — bu funksiya o'zi
    tekshirmaydi, chaqiruvchi tomonda tekshirilishi kerak (UI shu ishni
    qiladi). Fayllarni diskdan o'chirmaydi — faqat baza yozuvini.
    """
    if not xat_ids:
        return 0
    conn = get_conn()
    placeholders = ','.join('?' * len(xat_ids))
    cur = conn.execute(f"DELETE FROM xatlar WHERE id IN ({placeholders})", xat_ids)
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n


def get_xatlar_ids_by_holat(holat):
    """Berilgan holatdagi (masalan 'tayyor') barcha xat ID'larini qaytaradi."""
    conn = get_conn()
    rows = conn.execute("SELECT id FROM xatlar WHERE holat=?", (holat,)).fetchall()
    conn.close()
    return [r['id'] for r in rows]


def davo_ariza_mavjudmi(anketa_raqami):
    """
    Berilgan anketa raqami uchun (istalgan xat yozuvida) allaqachon Davo
    ariza tayyorlangan-tayyorlanmaganini tekshiradi — bitta anketaga
    faqat bitta Davo ariza yaratilishi kerak.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM xatlar WHERE anketa_raqami=? AND davo_ariza_fayl_yoli IS NOT NULL LIMIT 1",
        (anketa_raqami,)
    ).fetchone()
    conn.close()
    return row is not None


def reset_davo_ariza(xat_id):
    """
    Tayyorlangan Davo arizani (fayl, holat, tur, summa, ish raqami) bazadan
    tozalaydi — mijoz qaytadan "Davo ariza tayyorlash kerak" bosqichiga
    qaytadi va yangi Davo ariza yaratish mumkin bo'ladi. Sud bosqichiga
    o'tib ketgan (sud_holati='topshirildi') ishlar UCHUN ishlatilmasligi
    kerak — bu holatda avval sud yozuvi tozalanishi kerak bo'ladi.
    """
    conn = get_conn()
    conn.execute('''
        UPDATE xatlar SET davo_ariza_fayl_yoli=NULL, davo_ariza_holati=NULL,
            davo_ariza_turi=NULL, davo_ariza_sana=NULL, davo_ariza_ish_raqami=NULL,
            davo_ariza_imzo_sana=NULL, davo_summasi_asosiy=NULL, davo_summasi_foiz=NULL,
            davo_summasi_jarima=NULL, qoshimcha_davo_kerak=NULL
        WHERE id=?
    ''', (xat_id,))
    conn.commit()
    conn.close()


def mark_davo_ariza_yaratildi(xat_id, fayl_yoli, turi=None, portfel_row=None):
    """
    Davo ariza yaratilganda, davo summasini (jami muddati o'tgan qarz:
    asosiy + foiz + jarima) "surat" sifatida saqlaydi — keyinchalik
    Palatadan qaytganda joriy qarzdorlik bilan solishtirish uchun kerak
    bo'ladi.
    """
    conn = get_conn()
    now = datetime.datetime.now().isoformat()
    asosiy = foiz = jarima = None
    if portfel_row:
        asosiy = portfel_row.get('asosiy_qarz', 0) or 0
        foiz = portfel_row.get('foiz_qarz', 0) or 0
        jarima = portfel_row.get('jarima', 0) or 0
    conn.execute(
        "UPDATE xatlar SET davo_ariza_sana=?, davo_ariza_fayl_yoli=?, davo_ariza_holati='tayyor', "
        "davo_ariza_turi=?, davo_summasi_asosiy=?, davo_summasi_foiz=?, davo_summasi_jarima=? "
        "WHERE id=?",
        (now, fayl_yoli, turi, asosiy, foiz, jarima, xat_id))
    conn.commit()
    conn.close()


def get_davo_ariza_farqi(xat, portfel_row, settings=None):
    """
    Davo ariza yaratilgan paytdagi davo summasi (surat) bilan bugungi
    joriy qarzdorlikni solishtiradi. Agar joriy qarz davo summasidan
    1 BXMdan ko'proq oshib ketgan bo'lsa — qo'shimcha (farq summasiga)
    yangi SSP davo ariza kiritish va sudga yo'naltirish talab qilinadi.
    """
    if settings is None:
        settings = get_all_settings()
    bxm = float(settings.get('bxm_miqdori', 375000) or 375000)

    davo_summasi = (xat.get('davo_summasi_asosiy') or 0) + (xat.get('davo_summasi_foiz') or 0) + \
        (xat.get('davo_summasi_jarima') or 0)
    joriy_qarz = (portfel_row.get('asosiy_qarz', 0) or 0) + (portfel_row.get('foiz_qarz', 0) or 0) + \
        (portfel_row.get('jarima', 0) or 0)
    farq = joriy_qarz - davo_summasi

    return {
        'davo_summasi': davo_summasi,
        'davo_summasi_asosiy': xat.get('davo_summasi_asosiy') or 0,
        'davo_summasi_foiz': xat.get('davo_summasi_foiz') or 0,
        'davo_summasi_jarima': xat.get('davo_summasi_jarima') or 0,
        'joriy_qarz': joriy_qarz,
        'farq': farq,
        'qoshimcha_kerak': farq > bxm,
    }


def update_davo_ariza_fayl(xat_id, fayl_yoli):
    """Davo ariza faylini yangi (masalan SSPdan tasdiqlangan skan) fayl bilan almashtiradi."""
    conn = get_conn()
    conn.execute('UPDATE xatlar SET davo_ariza_fayl_yoli=? WHERE id=?', (fayl_yoli, xat_id))
    conn.commit()
    conn.close()


def mark_davo_ariza_olib_kelindi(xat_id, ish_raqami, imzo_sana, portfel_row=None, settings=None):
    """
    Davo ariza Palata/suddan ish raqami va imzo sanasi bilan qaytarilganda
    chaqiriladi. Shu bilan birga, davo summasi (yaratilgan paytdagi surat)
    bilan bugungi qarzdorlikni solishtirib, agar farq 1 BXMdan ko'p bo'lsa
    "qo'shimcha davo ariza kerak" bayrog'ini o'rnatadi.
    """
    conn = get_conn()
    qoshimcha_kerak = 0
    if portfel_row:
        xat = get_xat_by_id(xat_id)
        farqi = get_davo_ariza_farqi(xat, portfel_row, settings)
        qoshimcha_kerak = 1 if farqi['qoshimcha_kerak'] else 0
    conn.execute("UPDATE xatlar SET davo_ariza_holati='olib_kelindi', "
                 "davo_ariza_ish_raqami=?, davo_ariza_imzo_sana=?, qoshimcha_davo_kerak=? WHERE id=?",
                 (ish_raqami, imzo_sana, qoshimcha_kerak, xat_id))
    conn.commit()
    conn.close()
    return bool(qoshimcha_kerak)


def get_davo_ariza_pending_by_turi(turi):
    """Muayyan turdagi, hali 'olib_kelindi' bo'lmagan Davo arizalar ro'yxati."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar
        WHERE davo_ariza_turi=? AND davo_ariza_holati='tayyor'
    ''', (turi,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_sud_kiritilmadi(xat_id, sababi, sana, pdf_fayl=None, xodim_ism=None, izoh=None):
    """Tasdiqlanib (Olib kelindi) kelgan Davo ariza SUDGA topshirilmasligi
    kerak bo'lgan holatlarni, sababi bilan birga qayd qiladi:
      - 'qarz_yopilgan': qarz to'liq yopilgan (chaqiruvchi tomonidan
        oldindan tekshirilgan bo'lishi shart)
      - 'mijoz_arizasi': mijozning yozma arizasi asosida (PDF majburiy)
      - 'xodim_iltimosi': bank xodimi iltimosiga asosan (F.I.Sh + izoh)
    """
    conn = get_conn()
    conn.execute('''
        UPDATE xatlar SET sud_kiritilmadi_sababi=?, sud_kiritilmadi_pdf=?,
            sud_kiritilmadi_xodim_ism=?, sud_kiritilmadi_izoh=?, sud_kiritilmadi_sana=?
        WHERE id=?
    ''', (sababi, pdf_fayl, xodim_ism, izoh, sana, xat_id))
    conn.commit()
    conn.close()


def mark_sud_topshirildi(xat_id, ish_raqami, sana, buyruq_fayl=None):
    """Davo ariza sudga (Fuqarolik/Iqtisodiy) topshirilganda, ish raqami va sana bilan tasdiqlash."""
    conn = get_conn()
    conn.execute("UPDATE xatlar SET sud_holati='topshirildi', sud_ish_raqami=?, "
                 "sud_topshirilgan_sana=?, sud_buyrugi_fayl=COALESCE(?, sud_buyrugi_fayl) WHERE id=?",
                 (ish_raqami, sana, buyruq_fayl, xat_id))
    conn.commit()
    conn.close()


def get_sudga_topshirilganlar_royxati():
    """
    Sudga topshirilgan ('topshirildi') barcha ishlar ro'yxati — Excel'ga
    eksport qilish uchun (Chora ko'rish va Davo Ariza bo'limlaridan
    chaqiriladi). Har biriga tegishli portfel ma'lumoti ham qo'shib
    qaytariladi.
    """
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar WHERE sud_holati='topshirildi'
        ORDER BY sud_topshirilgan_sana DESC
    ''').fetchall()
    conn.close()
    natija = []
    for r in rows:
        rd = dict(r)
        prow = get_portfel_by_id(rd['portfel_id'])
        natija.append({'xat': rd, 'portfel': prow})
    return natija


def get_sud_topshirish_kerak():
    """
    Davo ariza 'olib_kelindi' (Palatadan/imzodan qaytgan) bo'lgan, lekin hali
    sudga topshirilmagan (sud_holati != 'topshirildi') VA "sudga
    kiritilmadi" deb (sababi bilan) alohida belgilanmagan mijozlar ro'yxati.
    MUHIM (himoya qatlami): agar biror sabab bilan (masalan eski xato
    tufayli) BITTA anketa uchun BIR NECHTA mos yozuv paydo bo'lib qolgan
    bo'lsa — faqat ENG SO'NGGI (id bo'yicha eng katta) yozuv ko'rsatiladi,
    aks holda bitta anketa ro'yxatda ikki marta chiqib, "Yig'ma jild/
    Ruxsat" holati amaliyotda yo'qolgandek ko'rinib qolar edi.
    """
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar
        WHERE davo_ariza_holati='olib_kelindi'
          AND (sud_holati IS NULL OR sud_holati != 'topshirildi')
          AND (sud_kiritilmadi_sababi IS NULL OR sud_kiritilmadi_sababi = '')
          AND (arxivlangan IS NULL OR arxivlangan=0)
        ORDER BY id ASC
    ''').fetchall()
    conn.close()
    eng_yaxshilar = {}
    for r in rows:
        rd = dict(r)
        anketa = rd['anketa_raqami']
        joriy = eng_yaxshilar.get(anketa)
        if joriy is None:
            eng_yaxshilar[anketa] = rd
            continue
        # MUHIM: "eng so'nggi (id)" emas, balki "ENG KO'P TARAQQIYOTGA EGA"
        # yozuvni tanlaymiz — aks holda, agar eski (haqiqiy) yozuvda
        # allaqachon Yig'ma jild/Ruxsat bo'lsa-yu, keyin xato bilan yangi
        # (bo'sh) yozuv qo'shilib qolgan bo'lsa, o'sha bo'sh yozuv eski,
        # to'g'ri taraqqiyotni "yashirib" qo'yishi mumkin edi.
        def bal(x):
            return (1 if x.get('sud_yigma_jild_titul_fayl') else 0) + \
                   (1 if x.get('sud_hujjatlar_ruxsat') else 0) + x['id'] * 0.0001
        if bal(rd) > bal(joriy):
            eng_yaxshilar[anketa] = rd
    natija = sorted(eng_yaxshilar.values(), key=lambda x: x.get('davo_ariza_imzo_sana') or '')
    return natija


def get_sud_kiritilmagan_royxati():
    """'Sudga kiritilmadi' deb sababi bilan qayd qilingan barcha ishlar."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar
        WHERE sud_kiritilmadi_sababi IS NOT NULL AND sud_kiritilmadi_sababi != ''
        ORDER BY sud_kiritilmadi_sana DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_sud_topshirish_muddati_otganlar(muddat_kun=None):
    """
    Palatadan/imzodan qaytgan ('olib_kelindi'), lekin belgilangan muddat
    ichida (standart 5 kun) sudga hali topshirilmagan mijozlar ro'yxati.
    Muddat davo_ariza_imzo_sana (kun.oy.yil) dan hisoblanadi.
    """
    if muddat_kun is None:
        muddat_kun = int(get_setting('sud_topshirish_muddati_kun', 5))
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar
        WHERE davo_ariza_holati='olib_kelindi'
          AND (sud_holati IS NULL OR sud_holati != 'topshirildi')
          AND davo_ariza_imzo_sana IS NOT NULL AND davo_ariza_imzo_sana != ''
    ''').fetchall()
    conn.close()
    natija = []
    now = datetime.datetime.now()
    for r in rows:
        try:
            imzo_dt = datetime.datetime.strptime(r['davo_ariza_imzo_sana'], '%d.%m.%Y')
        except (ValueError, TypeError, AttributeError):
            continue
        if (now - imzo_dt).days > muddat_kun:
            natija.append(dict(r))
    return natija


def mark_mib_otkazildi(xat_id, mib_ish_raqami, mib_sana, ijro_varaqasi_fayl, mib_ijro_summasi=None,
                        sud_buyrugi_fayl=None):
    """
    Hujjat MIBga (Ijro byurosiga) o'tkazilganda, ijro varaqasi va MIB ish raqami
    bilan tasdiqlash. mib_ijro_summasi — o'tkazish paytidagi qarz summasi
    (surat sifatida saqlanadi, keyinchalik qarz o'sishini kuzatish uchun).
    sud_buyrugi_fayl — agar shu bosqichda ilova qilinsa, sud buyrug'i/hal
    qiluv qarori PDF fayli ham saqlanadi.
    """
    conn = get_conn()
    if sud_buyrugi_fayl:
        conn.execute("UPDATE xatlar SET mib_holati='otkazildi', mib_ish_raqami=?, "
                     "mib_otkazilgan_sana=?, ijro_varaqasi_fayl=?, mib_ijro_summasi=?, "
                     "sud_buyrugi_fayl=? WHERE id=?",
                     (mib_ish_raqami, mib_sana, ijro_varaqasi_fayl, mib_ijro_summasi,
                      sud_buyrugi_fayl, xat_id))
    else:
        conn.execute("UPDATE xatlar SET mib_holati='otkazildi', mib_ish_raqami=?, "
                     "mib_otkazilgan_sana=?, ijro_varaqasi_fayl=?, mib_ijro_summasi=? WHERE id=?",
                     (mib_ish_raqami, mib_sana, ijro_varaqasi_fayl, mib_ijro_summasi, xat_id))
    conn.commit()
    conn.close()


def mark_yigma_jild_yaratildi(xat_id, papka_yoli, titul_fayl_yoli):
    """Ijro harakati uchun yig'ma jild (papka + titul) yaratilganda belgilash."""
    conn = get_conn()
    conn.execute("UPDATE xatlar SET yigma_jild_papka=?, yigma_jild_titul_fayl=?, "
                 "yigma_jild_holati='mavjud' WHERE id=?",
                 (papka_yoli, titul_fayl_yoli, xat_id))
    conn.commit()
    conn.close()


def get_mib_otkazish_kerak():
    """Sudga topshirilgan, hali MIBga o'tkazilmagan (yoki sud qarori
    yuklanmagan) BARCHA mijozlar ro'yxati. MUHIM (soddalashtirildi):
    endi "Qaror kutilayotganlar" alohida bosqich EMAS — sud qarori
    (bank foydasiga/qisman/rad etildi) MIBga o'tkazish oynasining O'ZIDA
    so'raladi. Agar qaror allaqachon 'rad_etildi' deb qayd etilgan bo'lsa,
    bu ro'yxatga chiqarilmaydi (chunki bunday ishni MIBga o'tkazib
    bo'lmaydi).
    MUHIM: agar shu anketa uchun (masalan xat qayta-qayta yaratilib
    ketgani sababli) BOSHQA bir yozuvda MIBga allaqachon o'tkazilgan
    VA HALI YAKUNLANMAGAN (faol) bo'lsa — bu anketa bu ro'yxatga QAYTA
    CHIQARILMAYDI. LEKIN agar o'sha eski MIB ishi ALLAQACHON YAKUNLANGAN
    bo'lsa (mib_yakunlangan=1, masalan qarz to'liq to'langani uchun), bu
    ENDI YANGI SIKL (mijoz qayta qarzga botgani) deb hisoblanadi va
    to'sqinlik qilmaydi — aks holda, bir marta MIBdan to'liq chiqqan
    mijoz, qayta qarzdor bo'lib qolsa ham, ABADIY MIBga o'tkazib
    bo'lmay qolar edi."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar x1
        WHERE x1.sud_holati='topshirildi'
          AND (x1.sud_qaror_natija IS NULL OR x1.sud_qaror_natija != 'rad_etildi')
          AND (x1.mib_holati IS NULL OR x1.mib_holati != 'otkazildi')
          AND (x1.arxivlangan IS NULL OR x1.arxivlangan = 0)
          AND NOT EXISTS (
              SELECT 1 FROM xatlar x2
              WHERE x2.anketa_raqami = x1.anketa_raqami AND x2.mib_holati='otkazildi'
                AND (x2.mib_yakunlangan IS NULL OR x2.mib_yakunlangan = 0)
          )
        ORDER BY sud_topshirilgan_sana ASC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_legacy_sud_xat(portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi,
                           sud_ish_raqami, sud_sana, sud_buyrugi_fayl=None):
    """
    Bu dasturdan tashqarida avvalroq sudga topshirilgan, hozir bazada
    umuman mavjud bo'lmagan eski sud ishini ro'yxatga olish uchun.
    Xat/Davo ariza bosqichlari "o'tilgan" deb belgilanadi (aniq tarixiy
    sanalar bo'lmagani uchun sud sanasidan foydalaniladi).

    Agar sud_buyrugi_fayl berilmasa — ish hali HAL BO'LMAGAN (sudda
    ko'rilmoqda) deb hisoblanadi va "Suddan o'tkazilgan / MIB jarayonida"
    ro'yxatida "Kutilmoqda" holatida ko'rinadi (MIBga hali o'tkazish
    mumkin emas — chunki sud qarori/buyrug'i hali yo'q). Agar
    sud_buyrugi_fayl berilsa — ish hal bo'lgan deb hisoblanadi, MIBga
    o'tkazishga tayyor bo'ladi.
    """
    conn = get_conn()
    now_iso = datetime.datetime.now().isoformat()
    xat_turi = 'Talabnoma' if mijoz_turi in ('yuridik', 'yatt') else 'Ogohlantirish'
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, xat_turi,
                             yaratilgan_sana, muddat_sana, holat, yuborilgan_sana, fayl_yoli,
                             davo_ariza_sana, davo_ariza_holati,
                             sud_holati, sud_topshirilgan_sana, sud_ish_raqami, sud_buyrugi_fayl)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'yuborildi', ?, '', ?, 'olib_kelindi',
                'topshirildi', ?, ?, ?)
    ''', (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, xat_turi,
          now_iso, now_iso, now_iso, now_iso, sud_sana, sud_ish_raqami, sud_buyrugi_fayl))
    conn.commit()
    xid = cur.lastrowid
    conn.close()
    return xid


def create_legacy_mib_xat(portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi,
                           mib_ish_raqami, mib_sana, ijro_varaqasi_fayl=None,
                           sud_ish_raqami=None, joriy_qarzdorlik=None):
    """
    Bu dasturdan tashqarida (avvalroq) MIBga chiqarilgan, hozir bazada
    umuman mavjud bo'lmagan eski ishni to'g'ridan-to'g'ri MIB bosqichida
    ro'yxatga olish uchun. Xat/Davo ariza/Sud bosqichlari "o'tilgan" deb
    belgilanadi (aniq tarixiy sanalar bo'lmagani uchun MIB sanasidan
    foydalaniladi), shundan keyin MIB bazasi va nazorat funksiyalari
    (masalan 15 kunlik harakatsizlik ogohlantirishi) shu yozuv uchun ham
    to'liq ishlay boshlaydi.

    sud_ish_raqami — agar ma'lum bo'lsa, sud ishi raqami ham saqlanadi.
    joriy_qarzdorlik — agar foydalanuvchi hozirgi (MIBda turgan) aniq
    qarz summasini qo'lda kiritsa, mib_ijro_summasi shu summa bilan
    (portfeldagi avtomatik hisoblangan summa o'rniga) belgilanadi — bu
    ko'pincha portfeldagi joriy raqamdan aniqroq bo'ladi (masalan MIBda
    qisman undirilgan bo'lsa).
    """
    conn = get_conn()
    now_iso = datetime.datetime.now().isoformat()
    xat_turi = 'Talabnoma' if mijoz_turi in ('yuridik', 'yatt') else 'Ogohlantirish'
    prow = conn.execute('SELECT * FROM portfel WHERE id=?', (portfel_id,)).fetchone()
    jami_qarz = 0
    if prow:
        jami_qarz = (prow['asosiy_qarz'] or 0) + (prow['foiz_qarz'] or 0) + (prow['jarima'] or 0)
    if joriy_qarzdorlik is not None:
        jami_qarz = joriy_qarzdorlik
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, xat_turi,
                             yaratilgan_sana, muddat_sana, holat, yuborilgan_sana, fayl_yoli,
                             davo_ariza_sana, davo_ariza_holati,
                             sud_holati, sud_topshirilgan_sana, sud_ish_raqami,
                             mib_holati, mib_ish_raqami, mib_otkazilgan_sana, ijro_varaqasi_fayl,
                             mib_ijro_summasi)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'yuborildi', ?, '', ?, 'olib_kelindi',
                'topshirildi', ?, ?, 'otkazildi', ?, ?, ?, ?)
    ''', (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, xat_turi,
          now_iso, now_iso, now_iso, now_iso, mib_sana, sud_ish_raqami,
          mib_ish_raqami, mib_sana, ijro_varaqasi_fayl, jami_qarz))
    conn.commit()
    xid = cur.lastrowid
    conn.close()
    return xid


def yigma_jild_toldirish(jild_papka, xat):
    """
    Yig'ma jild yaratilganda, shu ishga tegishli AVVAL yaratilgan barcha
    hujjatlarni (Ogohlantirish/Talabnoma xati, Davo ariza, Sud buyrug'i,
    Ijro varaqasi) — qaysi biri mavjud bo'lsa — avtomatik ravishda jildga
    nusxalab qo'yadi. Fayl mavjud bo'lmasa, sekin o'tkazib yuboriladi.

    MUHIM (qo'shildi): kredit hujjatlari (Kredit shartnoma, Kafillik,
    Garov, Bank baholash) ham — bular Ijro byurosi uchun ham muhim dalil
    hujjatlari — avtomatik qo'shiladi. Agar JORIY sikl xatida bu
    hujjatlar bo'lmasa (masalan Sud bosqichida boshqa xat yozuvida
    yuklangan bo'lsa), tizim ULARNI HAM: 1) shu anketaning OLDINGI
    xat yozuvlaridan, 2) yoki DOIMIY kredit hujjatlar arxividan
    (kredit_hujjatlar_arxiv jadvali — hatto "Nollashtirish" qilingan
    bo'lsa ham saqlanib qoladi) avtomatik qidirib topadi."""
    import shutil
    if not jild_papka or not os.path.isdir(jild_papka):
        return
    hujjatlar = [
        ('fayl_yoli', '02_Xat_'),
        ('davo_ariza_fayl_yoli', '03_Davo_ariza_'),
        ('sud_buyrugi_fayl', '04_Sud_buyrugi_'),
        ('ijro_varaqasi_fayl', '01_Ijro_varaqasi_'),
        ('mib_yakunlash_hujjati_fayl', '05_Yakunlash_asosi_'),
    ]
    for maydon, prefiks in hujjatlar:
        manba = xat.get(maydon)
        if manba and os.path.exists(manba):
            allaqachon_bor = any(f.startswith(prefiks) for f in os.listdir(jild_papka))
            if not allaqachon_bor:
                ext = os.path.splitext(manba)[1]
                dest = os.path.join(jild_papka, f"{prefiks}{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}")
                shutil.copy2(manba, dest)

    kredit_hujjatlar = [
        ('kredit_shartnoma_fayl', '06_Kredit_shartnoma_'),
        ('kafillik_shartnoma_fayl', '07_Kafillik_shartnoma_'),
        ('garov_shartnoma_fayl', '08_Garov_shartnoma_'),
        ('bank_baholash_fayl', '09_Bank_baholash_'),
    ]
    conn = get_conn()
    oldingi_yozuvlar = conn.execute(
        'SELECT * FROM xatlar WHERE anketa_raqami=? AND id != ? ORDER BY id DESC',
        (xat.get('anketa_raqami'), xat.get('id'))).fetchall()
    arxiv_row = conn.execute(
        'SELECT * FROM kredit_hujjatlar_arxiv WHERE anketa_raqami=?', (xat.get('anketa_raqami'),)).fetchone()
    arxiv = dict(arxiv_row) if arxiv_row else {}
    conn.close()

    for maydon, prefiks in kredit_hujjatlar:
        manba = xat.get(maydon)
        if not manba or not os.path.exists(manba):
            for eski in oldingi_yozuvlar:
                eski = dict(eski)
                if eski.get(maydon) and os.path.exists(eski[maydon]):
                    manba = eski[maydon]
                    break
        if not manba or not os.path.exists(manba):
            if arxiv.get(maydon) and os.path.exists(arxiv[maydon]):
                manba = arxiv[maydon]
        if manba and os.path.exists(manba):
            allaqachon_bor = any(f.startswith(prefiks) for f in os.listdir(jild_papka))
            if not allaqachon_bor:
                ext = os.path.splitext(manba)[1]
                dest = os.path.join(jild_papka, f"{prefiks}{os.path.basename(manba)}")
                try:
                    shutil.copy2(manba, dest)
                except Exception:
                    pass


def get_mib_faol_royxat():
    """MIBga o'tkazilgan (undirish jarayonidagi, hali yakunlanmagan) barcha mijozlar ro'yxati."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar WHERE mib_holati='otkazildi' AND (mib_yakunlangan IS NULL OR mib_yakunlangan=0)
        ORDER BY mib_otkazilgan_sana DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mib_yakunlangan_royxati():
    """To'xtatilgan/yakunlangan (undirish tugatilgan) MIB ishlari ro'yxati."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar WHERE mib_holati='otkazildi' AND mib_yakunlangan=1
        ORDER BY mib_yakunlangan_sana DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_mib_yakunlandi(xat_id, sabab, sana=None):
    """MIB ijro ishini to'xtatilgan/yakunlangan deb belgilaydi — endi 'MIBda jarayondagi
    hujjatlar' faol ro'yxatidan chiqadi, 'Yakunlangan ishlar'da ko'rinadi."""
    if sana is None:
        sana = datetime.date.today().strftime('%d.%m.%Y')
    conn = get_conn()
    conn.execute('''
        UPDATE xatlar SET mib_yakunlangan=1, mib_yakunlangan_sana=?, mib_yakunlash_sababi=?
        WHERE id=?
    ''', (sana, sabab, xat_id))
    conn.commit()
    conn.close()


def set_mib_yakunlash_hujjati(xat_id, fayl_yoli):
    """MIB ishini yakunlash asosi bo'lgan hujjat (PDF) yo'lini saqlaydi."""
    conn = get_conn()
    conn.execute('UPDATE xatlar SET mib_yakunlash_hujjati_fayl=? WHERE id=?', (fayl_yoli, xat_id))
    conn.commit()
    conn.close()


def mib_ishni_qayta_ochish(xat_id):
    """Xato bilan yakunlangan MIB ishini qayta faol holatga qaytaradi."""
    conn = get_conn()
    conn.execute('UPDATE xatlar SET mib_yakunlangan=0 WHERE id=?', (xat_id,))
    conn.commit()
    conn.close()


def sud_kredit_hujjatlar_royxati(davo_ariza_turi):
    """Davo ariza turiga (oddiy/kafil/garov/kafil_garov) qarab, Sud harakatlari
    yig'ma jildi uchun QAYSI kredit hujjatlari kerakligini aniqlaydi.
    Har biri (maydon_nomi, ko'rsatish_nomi) juftligi sifatida qaytariladi.
    MUHIM: Ma'lumotnoma (sudga topshirishda) — IXTIYORIY hujjat, shuning
    uchun bu ro'yxatda (ya'ni "ruxsat berish" uchun MAJBURIY hujjatlar
    ro'yxatida) YO'Q — lekin foydalanuvchi xohlasa, baribir alohida
    tugma orqali yaratishi/yuklashi mumkin."""
    turi = davo_ariza_turi or ''
    royxat = [('kredit_shartnoma_fayl', 'Kredit shartnomasi')]
    if 'kafil' in turi:
        royxat.append(('kafillik_shartnoma_fayl', 'Kafillik shartnomasi'))
    if 'garov' in turi:
        royxat.append(('garov_shartnoma_fayl', 'Garov shartnomasi'))
        royxat.append(('bank_baholash_fayl', 'Bank baholashi'))
    return royxat


def sud_yigma_jild_yaratish(xat_id, papka_yoli, titul_fayl_yoli):
    conn = get_conn()
    conn.execute('UPDATE xatlar SET sud_yigma_jild_papka=?, sud_yigma_jild_titul_fayl=? WHERE id=?',
                 (papka_yoli, titul_fayl_yoli, xat_id))
    conn.commit()
    conn.close()


def sud_hujjat_saqlash(xat_id, maydon_nomi, fayl_yoli):
    """Sud yig'ma jildi uchun kerakli hujjatlardan birini (kredit shartnoma,
    kafillik, garov, bank baholash, ma'lumotnoma) saqlaydi.
    MUHIM: agar bu KREDIT hujjati (odatda o'zgarmaydigan, doimiy hujjat)
    bo'lsa — uni alohida, DOIMIY arxiv jadvaliga ham yozib qo'yamiz. Bu
    orqali, agar keyinchalik "Nollashtirish" orqali butun ish-yuritish
    tarixi o'chirilsa ham (masalan jarayon noldan qayta boshlansa), bu
    hujjatlar YO'QOLIB QOLMAYDI — keyingi safar Sud yig'ma jild
    yaratilganda AVTOMATIK topilib, qayta ishlatiladi."""
    if maydon_nomi not in ('kredit_shartnoma_fayl', 'kafillik_shartnoma_fayl', 'garov_shartnoma_fayl',
                            'bank_baholash_fayl', 'sud_malumotnoma_topshirishda_fayl', 'sud_malumotnoma_kun_fayl'):
        raise ValueError("Noto'g'ri maydon nomi")
    conn = get_conn()
    conn.execute(f'UPDATE xatlar SET {maydon_nomi}=? WHERE id=?', (fayl_yoli, xat_id))

    kredit_maydonlar = ('kredit_shartnoma_fayl', 'kafillik_shartnoma_fayl', 'garov_shartnoma_fayl', 'bank_baholash_fayl')
    if maydon_nomi in kredit_maydonlar:
        anketa_row = conn.execute('SELECT anketa_raqami FROM xatlar WHERE id=?', (xat_id,)).fetchone()
        if anketa_row:
            anketa = anketa_row['anketa_raqami']
            conn.execute('INSERT OR IGNORE INTO kredit_hujjatlar_arxiv (anketa_raqami) VALUES (?)', (anketa,))
            conn.execute(
                f'UPDATE kredit_hujjatlar_arxiv SET {maydon_nomi}=?, yangilangan_sana=? WHERE anketa_raqami=?',
                (fayl_yoli, datetime.datetime.now().isoformat(), anketa)
            )
    conn.commit()
    conn.close()


def mib_harakat_turi_qoshish(nomi):
    conn = get_conn()
    conn.execute('INSERT OR IGNORE INTO mib_harakat_turlari (nomi, faol) VALUES (?, 1)', (nomi,))
    conn.commit()
    conn.close()


def mib_harakat_turlari_royxati(faqat_faol=True):
    conn = get_conn()
    if faqat_faol:
        rows = conn.execute('SELECT * FROM mib_harakat_turlari WHERE faol=1 ORDER BY id ASC').fetchall()
    else:
        rows = conn.execute('SELECT * FROM mib_harakat_turlari ORDER BY id ASC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mib_harakat_turi_ochirish(turi_id):
    conn = get_conn()
    conn.execute('UPDATE mib_harakat_turlari SET faol=0 WHERE id=?', (turi_id,))
    conn.commit()
    conn.close()


def f95413_titul_saqlash(anketa_raqami, titul_fayl):
    conn = get_conn()
    conn.execute('''
        INSERT INTO f95413_titul (anketa_raqami, titul_fayl, yaratilgan_sana) VALUES (?, ?, ?)
        ON CONFLICT(anketa_raqami) DO UPDATE SET titul_fayl=excluded.titul_fayl, yaratilgan_sana=excluded.yaratilgan_sana
    ''', (anketa_raqami, titul_fayl, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


def f95413_titul_olish(anketa_raqami):
    conn = get_conn()
    row = conn.execute('SELECT * FROM f95413_titul WHERE anketa_raqami=?', (anketa_raqami,)).fetchone()
    conn.close()
    return dict(row) if row else None


def f95413_hujjat_qoshish(anketa_raqami, hujjat_nomi, fayl_yoli):
    conn = get_conn()
    conn.execute('''
        INSERT INTO f95413_hujjatlar (anketa_raqami, hujjat_nomi, fayl_yoli, yuklangan_sana)
        VALUES (?, ?, ?, ?)
    ''', (anketa_raqami, hujjat_nomi, fayl_yoli, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


def f95413_hujjatlar_royxati(anketa_raqami):
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM f95413_hujjatlar WHERE anketa_raqami=? ORDER BY id ASC', (anketa_raqami,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def f95413_hujjat_ochirish(hujjat_id):
    conn = get_conn()
    conn.execute('DELETE FROM f95413_hujjatlar WHERE id=?', (hujjat_id,))
    conn.commit()
    conn.close()


def sud_qoshimcha_hujjat_qoshish(xat_id, hujjat_nomi, fayl_yoli):
    """Sud yig'ma jildiga, standart ro'yxatda bo'lmagan, IXTIYORIY qo'shimcha
    hujjat (foydalanuvchi o'zi nom bergan) qo'shadi."""
    conn = get_conn()
    conn.execute('''
        INSERT INTO sud_qoshimcha_hujjatlar (xat_id, hujjat_nomi, fayl_yoli, yuklangan_sana)
        VALUES (?, ?, ?, ?)
    ''', (xat_id, hujjat_nomi, fayl_yoli, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


def sud_qoshimcha_hujjatlar_royxati(xat_id):
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM sud_qoshimcha_hujjatlar WHERE xat_id=? ORDER BY id ASC', (xat_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def sud_qoshimcha_hujjat_ochirish(hujjat_id):
    conn = get_conn()
    conn.execute('DELETE FROM sud_qoshimcha_hujjatlar WHERE id=?', (hujjat_id,))
    conn.commit()
    conn.close()


def sud_hujjatlar_toliqmi(xat):
    """Davo ariza turiga qarab kerakli barcha hujjatlar (Titul, Ma'lumotnoma,
    Davo ariza, Xat, kredit hujjatlari) yuklanganini tekshiradi — sudga
    yuborishga ruxsat berish uchun."""
    kerakli = sud_kredit_hujjatlar_royxati(xat.get('davo_ariza_turi'))
    for maydon, _ in kerakli:
        if not xat.get(maydon):
            return False
    return bool(xat.get('sud_yigma_jild_titul_fayl') and xat.get('davo_ariza_fayl_yoli') and xat.get('fayl_yoli'))


def sud_hujjatlar_ruxsat_berish(xat_id):
    conn = get_conn()
    conn.execute('UPDATE xatlar SET sud_hujjatlar_ruxsat=1 WHERE id=?', (xat_id,))
    conn.commit()
    conn.close()


def sud_qaror_saqlash(xat_id, natija, fayl_yoli, sana, qisman_asosiy=0, qisman_foiz=0, qisman_penya=0, davlat_boji_sherik=False, rad_sababi=None):
    """Sud qarorini (Bank foydasiga / Qisman / Rad etildi) saqlaydi.
    Bank foydasiga yoki Qisman bo'lsa — sud ishi tugab, MIB jarayoni uchun
    tayyor holatga o'tadi (mib_ish_boshlash_kerak orqali alohida belgilanadi).
    Rad etilsa — ish yakunlanadi, sabab bilan."""
    conn = get_conn()
    conn.execute('''
        UPDATE xatlar SET sud_qaror_fayl=?, sud_qaror_natija=?, sud_qaror_sana=?,
            sud_qisman_asosiy_farq=?, sud_qisman_foiz_farq=?, sud_qisman_penya_farq=?,
            sud_qisman_davlat_boji_sherik=?, sud_rad_sababi=?
        WHERE id=?
    ''', (fayl_yoli, natija, sana, qisman_asosiy, qisman_foiz, qisman_penya,
          1 if davlat_boji_sherik else 0, rad_sababi, xat_id))
    conn.commit()
    conn.close()


def sud_qaror_muddati_kun(mijoz_turi):
    """Sud qarori yuklanishi kerak bo'lgan muddat: Fuqarolik (jismoniy) — 5
    kun, Iqtisodiy (yuridik/YaTT) — 15 kun."""
    return 15 if mijoz_turi in ('yuridik', 'yatt') else 5


def mib_ijro_varaqasi_muddati_kun(mijoz_turi):
    """Sud qarori 'bank foydasiga'/'qisman' bo'lgandan keyin, Ijro varaqasini
    tizimga yuklash muddati: Fuqarolik — 15 kun, Iqtisodiy — 30 kun."""
    return 30 if mijoz_turi in ('yuridik', 'yatt') else 15


def get_sud_qaror_kutilayotganlar():
    """Sudga topshirilgan, lekin hali qaror (5/15 kunlik muddatda) yuklanmagan
    ishlar ro'yxati — muddat holatini ko'rsatib beradi."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar WHERE sud_holati='topshirildi'
          AND (sud_qaror_natija IS NULL OR sud_qaror_natija = '')
          AND (mib_holati IS NULL OR mib_holati != 'otkazildi')
          AND (arxivlangan IS NULL OR arxivlangan = 0)
        ORDER BY sud_topshirilgan_sana ASC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ------------------- Sud kunlari (Reja Grafik) -------------------

def sud_kuni_qoshish(anketa_raqami, mijoz_nomi, sud_sanasi, sud_vaqti, sud_nomi, sud_ish_raqami):
    conn = get_conn()
    conn.execute('''
        INSERT INTO sud_kunlari (anketa_raqami, mijoz_nomi, sud_sanasi, sud_vaqti, sud_nomi,
            sud_ish_raqami, yaratilgan_sana)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (anketa_raqami, mijoz_nomi, sud_sanasi, sud_vaqti, sud_nomi, sud_ish_raqami,
          datetime.datetime.now().isoformat()))
    conn.commit()
    # MUHIM: sud ish raqami berilgan bo'lsa, uni shu anketaning yig'ma jild
    # titulida va boshqa tegishli joylarida ham AVTOMATIK to'ldiramiz.
    if sud_ish_raqami:
        conn.execute('UPDATE xatlar SET sud_ish_raqami=? WHERE anketa_raqami=?', (sud_ish_raqami, anketa_raqami))
        conn.commit()
    conn.close()


def sud_kunlari_royxati():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM sud_kunlari ORDER BY sud_sanasi ASC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def sud_kuni_ochirish(sud_kuni_id):
    conn = get_conn()
    conn.execute('DELETE FROM sud_kunlari WHERE id=?', (sud_kuni_id,))
    conn.commit()
    conn.close()


def sud_kunlari_eslatmalari():
    """Bugungi kun uchun: ertaga sud bo'ladigan va bugun sud bo'ladigan
    (hali vaqti kelmagan) mijozlar ro'yxatini qaytaradi — eslatma uchun."""
    bugun = datetime.datetime.now().date()
    ertaga = bugun + datetime.timedelta(days=1)
    conn = get_conn()
    rows = conn.execute('SELECT * FROM sud_kunlari').fetchall()
    conn.close()
    ertangi, bugungi = [], []
    for r in rows:
        try:
            sana = datetime.datetime.strptime(r['sud_sanasi'], '%d.%m.%Y').date()
        except Exception:
            continue
        if sana == ertaga:
            ertangi.append(dict(r))
        elif sana == bugun:
            bugungi.append(dict(r))
    return {'ertaga': ertangi, 'bugun': bugungi}


# ------------------- Sud xarajatlari (pochta xarajatlari) -------------------

def sud_xarajat_qoshish(xat_id, anketa_raqami, mijoz_nomi, pinfl_yoki_stir, summa):
    conn = get_conn()
    conn.execute('''
        INSERT INTO sud_xarajatlar (xat_id, anketa_raqami, mijoz_nomi, pinfl_yoki_stir, summa,
            yaratilgan_sana) VALUES (?, ?, ?, ?, ?, ?)
    ''', (xat_id, anketa_raqami, mijoz_nomi, pinfl_yoki_stir, summa, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


def sud_xarajatlar_royxati():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM sud_xarajatlar ORDER BY id DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def sud_xarajat_mib_ish_ochish(xarajat_id, mib_ijro_ish_raqami):
    conn = get_conn()
    conn.execute("UPDATE sud_xarajatlar SET holati='mib_ochildi', mib_ijro_ish_raqami=? WHERE id=?",
                 (mib_ijro_ish_raqami, xarajat_id))
    conn.commit()
    conn.close()


def sud_xarajat_yakunlash(xarajat_id):
    conn = get_conn()
    conn.execute("UPDATE sud_xarajatlar SET holati='yakunlangan' WHERE id=?", (xarajat_id,))
    conn.commit()
    conn.close()


def sud_xarajatlar_tolov_moslashtirish_tekshirish():
    """Har bir 'mib_ochildi' holatidagi xarajat uchun, MIBdan kelgan
    to'lovlar orasida SHU XARAJAT SUMMASIGA to'liq teng keladigan
    tasdiqlangan to'lov bormi tekshiradi — bo'lsa, xarajatni avtomatik
    yakunlaydi (xuddi mib_ijro_ish_raqami bo'yicha to'landi deb)."""
    conn = get_conn()
    kutilayotganlar = conn.execute("SELECT * FROM sud_xarajatlar WHERE holati='mib_ochildi'").fetchall()
    yakunlangan_soni = 0
    for x in kutilayotganlar:
        mos_tolov = conn.execute('''
            SELECT id FROM tolovlar WHERE holati='tasdiqlangan' AND anketa_raqami=?
              AND ABS(summa - ?) < 1
        ''', (x['anketa_raqami'], x['summa'])).fetchone()
        if mos_tolov:
            conn.execute("UPDATE sud_xarajatlar SET holati='yakunlangan' WHERE id=?", (x['id'],))
            yakunlangan_soni += 1
    conn.commit()
    conn.close()
    return yakunlangan_soni


def dpd_asosida_mib_avtomatik_yakunlash():
    """Portfel har yangilanganda chaqiriladi. MIBda FAOL (mib_holati=
    'otkazildi', hali yakunlanmagan) barcha ishlar uchun — MIB monitoring
    holatini (get_mib_monitoring_holati) tekshiradi; agar natija
    'toxtatish' bo'lsa (qarzdorlik tugagan, YOKI DPD 'mib_toxtatish_dpd_
    chegara'dan (standart 30 kun) past bo'lib qolgan, YOKI undirilgan
    summa MIB summasiga yetgan) — MIB ishini AVTOMATIK yakunlaydi, va
    buning ASOSI sifatida hujjat yaratib biriktiradi."""
    import letters
    settings = get_all_settings()
    conn = get_conn()
    faol_ishlar = conn.execute('''
        SELECT * FROM xatlar
        WHERE mib_holati='otkazildi' AND (mib_yakunlangan IS NULL OR mib_yakunlangan=0)
          AND (arxivlangan IS NULL OR arxivlangan=0)
    ''').fetchall()

    yakunlangan_soni = 0
    for row in faol_ishlar:
        xat = dict(row)
        prow_row = conn.execute('SELECT * FROM portfel WHERE id=?', (xat['portfel_id'],)).fetchone()
        if not prow_row:
            continue
        prow = dict(prow_row)
        try:
            natija = get_mib_monitoring_holati(xat['id'], prow, xat=xat, settings=settings)
        except Exception:
            continue
        if not natija or natija.get('holat') != 'toxtatish':
            continue

        joriy_dpd = natija.get('dpd', 0)
        joriy_qarz = natija.get('jami_qarz', 0)
        eski_qarz = natija.get('mib_summasi', 0)
        try:
            asosiy_papka = settings.get('hujjatlar_papkasi', '').strip() or os.path.join(_app_dir(), 'yaratilgan_xatlar')
            papka = os.path.join(asosiy_papka, 'Huquqiy choralar', 'MIB avtomatik yakunlash',
                                  datetime.datetime.now().strftime('%d.%m.%Y'))
            os.makedirs(papka, exist_ok=True)
            fayl_yoli = os.path.join(
                papka, f"{letters.safe_filename(xat['mijoz_nomi'])}_{letters.safe_filename(xat['anketa_raqami'])}_yakunlash_asosi.docx")
            letters.generate_dpd_kamaygan_yakunlash_hujjati(
                fayl_yoli, xat, prow, joriy_dpd=joriy_dpd, eski_qarz=eski_qarz, joriy_qarz=joriy_qarz)
        except Exception:
            fayl_yoli = None

        mark_mib_yakunlandi(xat['id'], natija.get('xabar', "Avtomatik: DPD/qarz kamaygani sababli"))
        if fayl_yoli:
            set_mib_yakunlash_hujjati(xat['id'], fayl_yoli)
        yakunlangan_soni += 1

    conn.close()
    return yakunlangan_soni


def dpd_asosida_sud_tayyor_ishlarni_yakunlash():
    """Portfel har yangilanganda chaqiriladi. Davo ariza SSPdan tasdiqlanib
    qaytgan (sudga topshirilishi kutilayotgan), lekin hali sudga
    TOPSHIRILMAGAN ishlar uchun — agar JORIY portfel bo'yicha DPD yoki
    qarzdorlik chegaradan pastga tushib qolgan bo'lsa (masalan qisman
    yoki to'liq to'lov qilingani sababli) — bu Davo ariza ENDI SUDGA
    KERAK EMAS deb hisoblanadi:
      1) Tizim buni AVTOMATIK yakunlaydi (sud ishini "kiritilmadi" deb,
         'dpd_kamaygan_avtomatik' sababi bilan belgilaydi)
      2) Bu yakunlashning ASOSI sifatida hujjat yaratib, biriktiradi
      3) Hisobot ("Sudga kiritilmaganlar") bo'limida ko'rinadi
    Bu — Davo ariza HUJJATINI o'chirmaydi (huquqiy tayyorgarlik saqlanadi),
    faqat uni sudga YUBORMASLIKKA qaror qiladi."""
    settings = get_all_settings()
    dpd_ogoh = int(settings.get('dpd_chegara_kun', settings.get('chora_ogohlantirish_dpd_kun', 45)))
    conn = get_conn()
    tayyor_ishlar = conn.execute('''
        SELECT * FROM xatlar
        WHERE davo_ariza_holati='olib_kelindi'
          AND (sud_holati IS NULL OR sud_holati != 'topshirildi')
          AND (sud_kiritilmadi_sababi IS NULL OR sud_kiritilmadi_sababi = '')
          AND (arxivlangan IS NULL OR arxivlangan = 0)
    ''').fetchall()

    yakunlangan_soni = 0
    for row in tayyor_ishlar:
        xat = dict(row)
        prow_row = conn.execute('SELECT * FROM portfel WHERE id=?', (xat['portfel_id'],)).fetchone()
        if not prow_row:
            continue
        prow = dict(prow_row)
        joriy_dpd = prow.get('dpd_max') or 0
        joriy_qarz = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        eski_asosiy = xat.get('davo_summasi_asosiy') or 0
        eski_foiz = xat.get('davo_summasi_foiz') or 0
        eski_jarima = xat.get('davo_summasi_jarima') or 0
        eski_qarz = eski_asosiy + eski_foiz + eski_jarima

        # Yakunlash sharti: DPD chegaradan pastga tushgan, YOKI qarzdorlik
        # Davo ariza summasidan sezilarli darajada (kamida yarmiga) kamaygan
        dpd_pasaygan = joriy_dpd < dpd_ogoh
        qarz_keskin_kamaygan = eski_qarz > 0 and joriy_qarz < (eski_qarz * 0.5)
        if not (dpd_pasaygan or qarz_keskin_kamaygan):
            continue

        try:
            import letters
            mijoz_nomi_fayl = letters.safe_filename(xat.get('mijoz_nomi', ''))
            anketa_fayl = letters.safe_filename(xat.get('anketa_raqami', ''))
            papka = os.path.join(_app_dir(), 'sud_hujjatlar', 'Avtomatik_yakunlash')
            os.makedirs(papka, exist_ok=True)
            fayl_yoli = os.path.join(papka, f"{mijoz_nomi_fayl}_{anketa_fayl}_yakunlash_asosi.docx")
            letters.generate_dpd_kamaygan_yakunlash_hujjati(
                fayl_yoli, xat, prow, joriy_dpd=joriy_dpd,
                eski_qarz=eski_qarz, joriy_qarz=joriy_qarz)
        except Exception:
            fayl_yoli = None

        conn.execute('''
            UPDATE xatlar SET sud_kiritilmadi_sababi='dpd_kamaygan_avtomatik',
                sud_kiritilmadi_pdf=?, sud_kiritilmadi_izoh=?, sud_kiritilmadi_sana=?
            WHERE id=?
        ''', (fayl_yoli, f"DPD: {joriy_dpd} kun, Qarz: {joriy_qarz:,.0f} so'm".replace(',', ' '),
              datetime.datetime.now().strftime('%d.%m.%Y'), xat['id']))
        yakunlangan_soni += 1

    conn.commit()
    conn.close()
    return yakunlangan_soni


def dpd_asosida_sud_kiritilmagan_qayta_ochish():
    """Agar biror ish AVTOMATIK ravishda ('dpd_kamaygan_avtomatik' sababi
    bilan) 'Sudga kiritilmadi' deb yopilgan bo'lsa-yu, keyinchalik (portfel
    yangilanganda) DPD yana chegaradan OSHIB ketsa (mijoz yana to'lamay
    qo'ygani, holat yana yomonlashgani sababli) — tizim buni AVTOMATIK
    qayta ochadi (sud_kiritilmadi belgisini olib tashlaydi), shunda ish
    yana "SSPdan o'tib sudga jo'natiladiganlar" ro'yxatida ko'rinadi.
    MUHIM: bu FAQAT tizim o'zi yopgan holatlarga tegishli — xodim qo'lda
    'qarz_yopilgan'/'mijoz_arizasi'/'xodim_iltimosi' deb yopgan holatlarga
    HECH QACHON tegilmaydi, chunki bular inson qarori."""
    settings = get_all_settings()
    dpd_ogoh = int(settings.get('dpd_chegara_kun', settings.get('chora_ogohlantirish_dpd_kun', 45)))
    conn = get_conn()
    avtomatik_yopilganlar = conn.execute('''
        SELECT id, portfel_id, anketa_raqami FROM xatlar
        WHERE sud_kiritilmadi_sababi='dpd_kamaygan_avtomatik'
          AND (arxivlangan IS NULL OR arxivlangan = 0)
    ''').fetchall()

    qayta_ochilgan_soni = 0
    for row in avtomatik_yopilganlar:
        prow = conn.execute('SELECT dpd_max FROM portfel WHERE id=?', (row['portfel_id'],)).fetchone()
        joriy_dpd = prow['dpd_max'] if prow else 0
        if joriy_dpd is not None and joriy_dpd >= dpd_ogoh:
            conn.execute('''
                UPDATE xatlar SET sud_kiritilmadi_sababi=NULL, sud_kiritilmadi_pdf=NULL,
                    sud_kiritilmadi_xodim_ism=NULL, sud_kiritilmadi_izoh=NULL, sud_kiritilmadi_sana=NULL
                WHERE id=?
            ''', (row['id'],))
            qayta_ochilgan_soni += 1
    conn.commit()
    conn.close()
    return qayta_ochilgan_soni


def anketa_jarayonini_nollashtirish(anketa_raqami):
    """MUHIM AMAL: berilgan anketa uchun FAOL xat/Davo ariza/Sud/MIB
    jarayonini "yopib", mijozni "portfelga yangi kirgan, hech qanday
    harakat qilinmagan" holatiga qaytaradi — YANGI sikl boshlanishi uchun.

    MUHIM (o'zgartirildi): eski yozuv ENDI O'CHIRILMAYDI — buning o'rniga
    'arxivlangan=1' deb belgilanadi. Bu orqali:
      - Mijoz Talabnoma/Chora ko'rish/Sud/MIB kabi barcha FAOL ish
        ro'yxatlarida "yangi" sifatida ko'rinadi (arxivlangan yozuvlar bu
        ro'yxatlarga qo'shilmaydi);
      - LEKIN o'sha eski sikl TARIXI (qanday tugagani, Sud/MIB yig'ma
        jildlari bilan birga) "Anketa tarixi" orqali ABADIY saqlanib,
        keyin ham ko'rish mumkin bo'lib qoladi.
    Portfel va to'lovlar tarixi (haqiqiy pul harakati) DAXL QILINMAYDI.
    """
    conn = get_conn()
    xat = conn.execute(
        "SELECT id FROM xatlar WHERE anketa_raqami=? AND (arxivlangan IS NULL OR arxivlangan=0)",
        (anketa_raqami,)).fetchone()
    if xat:
        conn.execute('UPDATE xatlar SET arxivlangan=1 WHERE id=?', (xat['id'],))
    conn.commit()
    conn.close()
    return bool(xat)


def get_mib_faol_royxat_toliq():
    """
    MIBga o'tkazilgan barcha mijozlarning to'liq ma'lumotini (anketa, PINFL,
    F.I.Sh, qarzdorlik, MIB ish raqami) va ular bo'yicha qilingan BARCHA
    harakatlarni (mib_amallar) birga qaytaradi — Excel eksporti uchun.
    Har bir mijoz uchun kamida bitta qator (harakat bo'lmasa ham) bo'ladi.
    """
    faol = get_mib_faol_royxat()
    natija = []
    for x in faol:
        prow = get_portfel_by_id(x['portfel_id'])
        jami_qarz = 0
        pinfl = ''
        stir = ''
        if prow:
            jami_qarz = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
            pinfl = prow.get('pinfl', '') or ''
            stir = prow.get('stir', '') or ''
        amallar = get_mib_amallar(x['id'])
        if not amallar:
            natija.append({'xat': x, 'pinfl': pinfl, 'stir': stir, 'jami_qarz': jami_qarz, 'amal': None})
        else:
            for amal in amallar:
                natija.append({'xat': x, 'pinfl': pinfl, 'stir': stir, 'jami_qarz': jami_qarz, 'amal': amal})
    return natija


def add_mib_amal(xat_id, amal_turi, amal_sanasi, tavsif='', **qoshimcha):
    """
    Yangi MIB harakatini (jurnal yozuvini) qo'shadi.
    qoshimcha: mulk_nomi, mulk_soni, mulk_summasi, dalolatnoma_fayl (xatlov uchun),
               sotilgan_nomi, sotilgan_soni, sotilgan_summasi (to'g'ridan sotish uchun),
               auksion_sana, auksion_narxi, auksion_lot_raqami, auksion_rasmlar (auksion uchun)
    """
    conn = get_conn()
    now = datetime.datetime.now().isoformat()
    cols = ['xat_id', 'amal_turi', 'amal_sanasi', 'tavsif', 'undirilgan_summa', 'mulk_nomi', 'mulk_soni',
            'mulk_summasi', 'dalolatnoma_fayl', 'sotilgan_nomi', 'sotilgan_soni',
            'sotilgan_summasi', 'auksion_sana', 'auksion_narxi', 'auksion_lot_raqami',
            'auksion_rasmlar', 'yaratilgan_sana']
    values = {
        'xat_id': xat_id, 'amal_turi': amal_turi, 'amal_sanasi': amal_sanasi, 'tavsif': tavsif,
        'yaratilgan_sana': now,
    }
    values.update(qoshimcha)
    placeholders = ','.join(['?'] * len(cols))
    conn.execute(f"INSERT INTO mib_amallar ({','.join(cols)}) VALUES ({placeholders})",
                 [values.get(c) for c in cols])
    conn.commit()
    conn.close()


def get_mib_amallar(xat_id):
    """Bitta mijoz (xat) uchun barcha MIB harakatlari tarixi, sana bo'yicha tartiblangan."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM mib_amallar WHERE xat_id=? ORDER BY amal_sanasi DESC, id DESC
    ''', (xat_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mib_oxirgi_amal_sanasi(xat_id, mib_otkazilgan_sana):
    """
    Mijoz uchun oxirgi MIB harakati sanasini qaytaradi — agar hali birorta
    harakat qilinmagan bo'lsa, MIBga o'tkazilgan sanani qaytaradi.
    """
    conn = get_conn()
    row = conn.execute('''
        SELECT MAX(amal_sanasi) AS oxirgi FROM mib_amallar WHERE xat_id=?
    ''', (xat_id,)).fetchone()
    conn.close()
    if row and row['oxirgi']:
        return row['oxirgi']
    return mib_otkazilgan_sana


AVTO_HOLAT_NOMLARI = {
    'xatlanmagan': "Xatlanmagan",
    'taqiq': "Taqiq qo'yilgan",
    'qidiruv': "Qidiruvda",
    'xatlangan': "Xatlangan (topilgan)",
}


def add_avtomashina(xat_id, mashina_rusumi, davlat_raqami, mijoz_pinfl):
    conn = get_conn()
    now = datetime.datetime.now().isoformat()
    conn.execute('''
        INSERT INTO mib_avtomashinalar (xat_id, mashina_rusumi, davlat_raqami, mijoz_pinfl,
                                         holati, qoshilgan_sana)
        VALUES (?, ?, ?, ?, 'xatlanmagan', ?)
    ''', (xat_id, mashina_rusumi, davlat_raqami, mijoz_pinfl, now))
    conn.commit()
    conn.close()


def update_avtomashina_holati(mashina_id, holati, asoslovchi_hujjat_fayl=None, modda=None, sana=None):
    """holati: 'taqiq' / 'qidiruv' / 'xatlangan' / 'xatlanmagan'ga qaytarish uchun ham ishlatiladi."""
    conn = get_conn()
    if sana is None:
        sana = datetime.date.today().strftime('%d.%m.%Y')
    conn.execute('''
        UPDATE mib_avtomashinalar
        SET holati=?, asoslovchi_hujjat_fayl=COALESCE(?, asoslovchi_hujjat_fayl),
            modda=COALESCE(?, modda), holat_sanasi=?
        WHERE id=?
    ''', (holati, asoslovchi_hujjat_fayl, modda, sana, mashina_id))
    conn.commit()
    conn.close()


def get_avtomashinalar(xat_id):
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM mib_avtomashinalar WHERE xat_id=? ORDER BY id DESC', (xat_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_barcha_avtomashinalar():
    """Barcha MIB ishlariga tegishli avtomashinalar, mijoz/anketa ma'lumoti bilan birga."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT m.*, x.mijoz_nomi, x.anketa_raqami
        FROM mib_avtomashinalar m
        JOIN xatlar x ON x.id = m.xat_id
        ORDER BY m.id DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_xatlanmagan_avtomashinalar():
    return [m for m in get_barcha_avtomashinalar() if m['holati'] == 'xatlanmagan']


def get_qidiruv_avtomashinalar():
    return [m for m in get_barcha_avtomashinalar() if m['holati'] == 'qidiruv']


def get_mib_monitoring_holati(xat_id, portfel_row, xat=None, settings=None):
    """
    MIB ishi bo'yicha qarzdorlik va MIBga o'tkazish paytida qayd qilingan
    summani (mib_ijro_summasi) solishtirib, quyidagi holatlarni aniqlaydi:
      - 'toxtatish': qarzdorlik tugagan, yoki DPD past (30 kundan kam),
        yoki undirilgan summa dastlabki MIB summasiga teng/ko'p bo'lsa —
        MIB harakatini to'xtatish va ishni yakunlash tavsiya etiladi.
      - 'qoshimcha': joriy qarzdorlik MIBga o'tkazilgandagi summadan
        BXMning 1 barobaridan ko'proq oshib ketgan bo'lsa (foiz/jarima
        o'sishi hisobiga) — farq summasini qo'shimcha ijro harakatiga
        kiritish tavsiya etiladi.
      - None: alohida chora talab qilinmaydi.
    """
    if settings is None:
        settings = get_all_settings()
    if xat is None:
        xat = get_xat_by_id(xat_id)
    bxm = float(settings.get('bxm_miqdori', 375000) or 375000)
    dpd_chegara = int(settings.get('mib_toxtatish_dpd_chegara', 30))

    jami_qarz = (portfel_row.get('asosiy_qarz', 0) or 0) + (portfel_row.get('foiz_qarz', 0) or 0) + \
        (portfel_row.get('jarima', 0) or 0) + (portfel_row.get('balans_95413', 0) or 0)
    dpd = portfel_row.get('dpd_max', 0) or 0
    undirilgan = get_mib_undirilgan_summa(xat_id)
    mib_summasi = (xat.get('mib_ijro_summasi') if xat else None) or jami_qarz

    if jami_qarz <= 0 or dpd < dpd_chegara or undirilgan >= mib_summasi:
        sabab = []
        if jami_qarz <= 0:
            sabab.append("qarzdorlik tugagan")
        if dpd < dpd_chegara:
            sabab.append(f"DPD {dpd_chegara} kundan kam ({dpd} kun)")
        if undirilgan >= mib_summasi and mib_summasi > 0:
            sabab.append("undirilgan summa MIB summasiga teng/ko'p")
        return {
            'holat': 'toxtatish',
            'xabar': f"MIB harakatini to'xtatish va ishni yakunlash kerak ({', '.join(sabab)})",
            'jami_qarz': jami_qarz, 'undirilgan': undirilgan, 'dpd': dpd, 'mib_summasi': mib_summasi,
        }

    farq = jami_qarz - mib_summasi
    if farq > bxm:
        return {
            'holat': 'qoshimcha',
            'xabar': f"Joriy qarzdorlik MIBga o'tkazilgandagi summadan {farq:,.0f} so'mga "
                     f"ko'p (BXMdan katta) — farq summasini qo'shimcha ijro harakatiga "
                     f"kiritish kerak".replace(',', ' '),
            'jami_qarz': jami_qarz, 'undirilgan': undirilgan, 'farq': farq, 'dpd': dpd,
            'mib_summasi': mib_summasi,
        }

    return {'holat': None, 'jami_qarz': jami_qarz, 'undirilgan': undirilgan, 'dpd': dpd,
            'mib_summasi': mib_summasi}


def get_mib_undirilgan_summa(xat_id):
    """
    Ushbu MIB ishi bo'yicha jami undirilgan (qaytarilgan) summani hisoblaydi —
    oylik ish haqqidan tushganlar + to'g'ridan sotilganlar + auksionda
    sotilganlar yig'indisi.
    """
    conn = get_conn()
    row = conn.execute('''
        SELECT
            COALESCE(SUM(undirilgan_summa), 0) +
            COALESCE(SUM(sotilgan_summasi), 0) +
            COALESCE(SUM(auksion_narxi), 0) AS jami
        FROM mib_amallar WHERE xat_id=?
    ''', (xat_id,)).fetchone()
    conn.close()
    return row['jami'] or 0


def get_mib_harakatsizlar(muddat_kun=None):
    """
    MIBga o'tkazilgan, lekin belgilangan muddat (standart 15 kun) ichida
    hech qanday harakat (amal) qilinmagan mijozlar ro'yxati.
    """
    if muddat_kun is None:
        muddat_kun = int(get_setting('mib_harakatsizlik_muddati_kun', 15))
    faol = get_mib_faol_royxat()
    natija = []
    now = datetime.datetime.now()
    for x in faol:
        oxirgi_sana = get_mib_oxirgi_amal_sanasi(x['id'], x.get('mib_otkazilgan_sana'))
        if not oxirgi_sana:
            continue
        try:
            oxirgi_dt = datetime.datetime.strptime(oxirgi_sana, '%d.%m.%Y')
        except (ValueError, TypeError, AttributeError):
            continue
        kun_otdi = (now - oxirgi_dt).days
        if kun_otdi > muddat_kun:
            x2 = dict(x)
            x2['harakatsizlik_kun'] = kun_otdi
            natija.append(x2)
    return natija


def _turi_portfel_qatoridan(prow):
    """
    Portfel qatoridagi 'Мижоз тури' (LE/Individual) va "Жис/юр/Ятт коди"
    asosida jismoniy/yuridik/YaTT ekanini aniqlaydi (faqat KO'RSATISH
    uchun — util.turi_kodidan() bilan bir xil mantiq, lekin bu yerda
    (database.py) util modulini import qilib bo'lmaydi — aylanma import
    xavfi bo'lgani uchun mustaqil nusxa sifatida saqlanadi).
    """
    turi = str(prow.get('mijoz_turi') or '').strip().upper()
    if turi == 'LE':
        return 'yuridik'
    kod = str(prow.get('mijoz_turi_kodi') or '').strip()
    if kod == '11':
        return 'yatt'
    return 'jismoniy'


CHORA_NOMLARI = {
    'xat_yuborish': "Xat yuborilishi kerak",
    'xat_yuborish_keyingi_bosqich': "Xat yuborilishi kerak",
    'davo_ariza_tayyorlash': "Davo ariza tayyorlash kerak",
    'mib_harakat_boshlash': "MIBda harakat boshlash kerak",
    'sudga_kiritish_kerak': "Sudga kiritish kerak",
    'jarayon_qaytadan_tiklash_kerak': "Jarayonni qaytadan boshlash kerak",
}


def get_ish_kuni_rejasi():
    """
    Chora ko'rish ro'yxatidagi barcha ishlarni **turi bo'yicha alohida**
    (xat yuborish, Davo ariza tayyorlash, MIB ijro harakati), joriy oyning
    20-sanasigacha qolgan ish kunlariga (dushanba-juma) teng taqsimlab,
    bugungi reja/bajarildi/qoldi hisobini chiqaradi.

    Muhim: bu hisob har safar **joriy qolgan ish soniga** asoslanadi — agar
    bugungi reja to'liq bajarilmasa, bajarilmagan qism avtomatik ertangi
    kunga (va undan keyingi kunlarga) taqsimlanadi, chunki "jami ish" va
    "qolgan ish kuni" har doim jonli (real vaqtdagi) holatdan hisoblanadi.
    """
    now = datetime.datetime.now()
    today = now.date()

    deadline = today.replace(day=20)
    if today > deadline:
        if today.month == 12:
            deadline = deadline.replace(year=today.year + 1, month=1)
        else:
            deadline = deadline.replace(month=today.month + 1)

    ish_kunlari = 0
    d = today
    while d <= deadline:
        if d.weekday() < 5:  # 0=Dushanba ... 4=Juma
            ish_kunlari += 1
        d += datetime.timedelta(days=1)
    if ish_kunlari == 0:
        ish_kunlari = 1

    royxat = get_chora_korish_royxati()
    xat_jami = sum(1 for r in royxat if r['chora'] in ('xat_yuborish', 'xat_yuborish_keyingi_bosqich'))
    davo_jami = sum(1 for r in royxat if r['chora'] == 'davo_ariza_tayyorlash')
    mib_jami = sum(1 for r in royxat if r['chora'] == 'mib_harakat_boshlash')

    def reja_hisob(jami):
        return -(-jami // ish_kunlari) if jami > 0 else 0

    bugun_iso = today.isoformat()
    bugun_dmy = today.strftime('%d.%m.%Y')
    conn = get_conn()
    xat_bajarildi = conn.execute(
        "SELECT COUNT(DISTINCT anketa_raqami) c FROM xatlar WHERE yuborilgan_sana LIKE ?", (bugun_iso + '%',)
    ).fetchone()['c']
    davo_bajarildi = conn.execute(
        "SELECT COUNT(DISTINCT anketa_raqami) c FROM xatlar WHERE davo_ariza_sana LIKE ?", (bugun_iso + '%',)
    ).fetchone()['c']
    mib_bajarildi = conn.execute(
        "SELECT COUNT(*) c FROM mib_amallar WHERE amal_sanasi = ?", (bugun_dmy,)
    ).fetchone()['c']
    conn.close()

    def turkum(nomi, jami, bajarildi):
        reja = reja_hisob(jami)
        return {'nomi': nomi, 'jami': jami, 'reja': reja, 'bajarildi': bajarildi,
                'qoldi': max(reja - bajarildi, 0)}

    xat_turk = turkum("Ogohlantirish/Talabnoma xati", xat_jami, xat_bajarildi)
    davo_turk = turkum("Davo ariza", davo_jami, davo_bajarildi)
    mib_turk = turkum("MIB ijro harakati", mib_jami, mib_bajarildi)

    umumiy_reja = xat_turk['reja'] + davo_turk['reja'] + mib_turk['reja']
    umumiy_bajarildi = xat_bajarildi + davo_bajarildi + mib_bajarildi
    foiz = round(umumiy_bajarildi / umumiy_reja * 100) if umumiy_reja > 0 else 0

    return {
        'deadline': deadline.strftime('%d.%m.%Y'),
        'ish_kunlari_qolgan': ish_kunlari,
        'jami_ish': xat_jami + davo_jami + mib_jami,
        'umumiy_reja': umumiy_reja,
        'umumiy_bajarildi': umumiy_bajarildi,
        'foiz': foiz,
        'ish_vaqti_tugadimi': now.hour >= 18,
        'turkumlar': [xat_turk, davo_turk, mib_turk],
    }


def _ish_kunlari_orasida(sana1_dt, sana2_dt):
    """Ikki sana orasidagi ish kunlari (dushanba-juma) sonini hisoblaydi."""
    if sana2_dt < sana1_dt:
        sana1_dt, sana2_dt = sana2_dt, sana1_dt
    kunlar = 0
    d = sana1_dt
    while d < sana2_dt:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            kunlar += 1
    return kunlar


def mark_vafot_etgan(portfel_id, anketa_raqami, mijoz_nomi, vafot_sanasi,
                      olimlik_guvohnomasi_fayl, pasport_fayl):
    """
    Mijozni vafot etgan deb ro'yxatga oladi. Kredit tugash sanasi bilan
    solishtirib, sug'urta polisi muddati o'tgan-o'tmaganini avtomatik
    aniqlaydi (odatda polis muddati kredit tugash sanasi bilan bir xil).
    """
    conn = get_conn()
    prow = conn.execute('SELECT * FROM portfel WHERE id=?', (portfel_id,)).fetchone()
    tugash_sanasi = prow['shartnoma_tugash_sanasi'] if prow else None

    polis_holati = 'tekshirilmagan'
    if tugash_sanasi:
        try:
            vafot_dt = datetime.datetime.strptime(vafot_sanasi, '%d.%m.%Y')
            tugash_dt = datetime.datetime.strptime(str(tugash_sanasi)[:10], '%d.%m.%Y')
            polis_holati = 'amalda' if vafot_dt <= tugash_dt else 'muddati_otgan'
        except (ValueError, TypeError, AttributeError):
            polis_holati = 'tekshirilmagan'

    now = datetime.datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO vafot_etganlar (portfel_id, anketa_raqami, mijoz_nomi, vafot_sanasi,
                                     olimlik_guvohnomasi_fayl, pasport_fayl, kredit_tugash_sanasi,
                                     polis_holati, yaratilgan_sana)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (portfel_id, anketa_raqami, mijoz_nomi, vafot_sanasi, olimlik_guvohnomasi_fayl,
          pasport_fayl, tugash_sanasi, polis_holati, now))
    conn.commit()
    vid = cur.lastrowid
    conn.close()
    return vid, polis_holati


def update_sugurta_malumot(vafot_id, sugurta_kompaniya, sugurta_polis_raqam, sugurta_polis_fayl):
    conn = get_conn()
    conn.execute('''
        UPDATE vafot_etganlar SET sugurta_kompaniya=?, sugurta_polis_raqam=?,
               sugurta_polis_fayl=? WHERE id=?
    ''', (sugurta_kompaniya, sugurta_polis_raqam, sugurta_polis_fayl, vafot_id))
    conn.commit()
    conn.close()


def mark_xabarnoma_yuborildi(vafot_id, sana, xabarnoma_fayl=None):
    conn = get_conn()
    conn.execute('''
        UPDATE vafot_etganlar SET xabarnoma_holati='yuborildi', xabarnoma_yuborilgan_sana=?
        WHERE id=?
    ''', (sana, vafot_id))
    conn.commit()
    conn.close()


def mark_sugurta_javob_keldi(vafot_id, sana, javob_fayl=None):
    conn = get_conn()
    conn.execute('''
        UPDATE vafot_etganlar SET xabarnoma_holati='javob_keldi', javob_kelgan_sana=?,
               javob_fayl=? WHERE id=?
    ''', (sana, javob_fayl, vafot_id))
    conn.commit()
    conn.close()


def get_vafot_etganlar_royxati():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM vafot_etganlar ORDER BY id DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_vafot_etgan_by_id(vafot_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM vafot_etganlar WHERE id=?', (vafot_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def is_anketa_vafot_etgan(anketa_raqami):
    """
    Anketa raqami vafot etganlar ro'yxatida bormi va sug'urta muddati
    o'tmaganmi (ya'ni hali jarayon davom etayotganmi) — bo'lsa, bu mijozga
    nisbatan boshqa hech qanday chora (xat/Davo ariza/MIB) ko'rilmasligi
    kerak, chunki jarayon vafot/sug'urta yo'nalishida davom etmoqda.
    """
    conn = get_conn()
    row = conn.execute('''
        SELECT id FROM vafot_etganlar WHERE anketa_raqami=? LIMIT 1
    ''', (anketa_raqami,)).fetchone()
    conn.close()
    return row is not None


def get_sugurta_javob_kutilayotganlar():
    """
    Xabarnoma yuborilgan, lekin belgilangan muddat (standart 40 ish kuni)
    ichida sug'urta kompaniyasidan javob kelmagan mijozlar ro'yxati.
    """
    muddat_kun = int(get_setting('sugurta_javob_muddati_ish_kun', 40))
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM vafot_etganlar
        WHERE xabarnoma_holati='yuborildi' AND xabarnoma_yuborilgan_sana IS NOT NULL
    ''').fetchall()
    conn.close()
    natija = []
    bugun = datetime.datetime.now()
    for r in rows:
        rd = dict(r)
        try:
            yub_dt = datetime.datetime.strptime(rd['xabarnoma_yuborilgan_sana'], '%d.%m.%Y')
        except (ValueError, TypeError, AttributeError):
            continue
        ish_kun_otdi = _ish_kunlari_orasida(yub_dt, bugun)
        if ish_kun_otdi > muddat_kun:
            rd['ish_kun_otdi'] = ish_kun_otdi
            natija.append(rd)
    return natija


def get_95413_royxati():
    """
    "Колдик 95413" balansiga ega (balansdan maxsus nazoratga o'tkazilgan)
    barcha kreditlarni, ularning DPD holatidan qat'i nazar, to'liq
    bosqichma-bosqich holati bilan qaytaradi: xat yuborilganmi, Davo ariza
    tayyorlanganmi, sudga topshirilganmi, MIBga o'tkazilganmi, yig'ma jild
    mavjudmi va MIB nazorat holati (agar MIB bosqichida bo'lsa).

    Bu kreditlar odatda asosiy balansdan chiqarilgani uchun DPD ko'rsatkichi
    past/nol bo'ladi va shu sabab boshqa DPD-asoslangan bo'limlarda
    (Tahlil, Chora ko'rish) umuman ko'rinmay qolishi mumkin edi — shuning
    uchun bu yerda alohida, DPD chegarasisiz nazorat qilinadi.
    """
    conn = get_conn()
    portfel_rows = conn.execute(
        "SELECT * FROM portfel WHERE balans_95413 IS NOT NULL AND balans_95413 != 0 AND faol=1"
    ).fetchall()
    portfel_rows = [dict(r) for r in portfel_rows]

    vafot_anketalar = {r['anketa_raqami'] for r in conn.execute(
        'SELECT DISTINCT anketa_raqami FROM vafot_etganlar').fetchall()}

    portfel_ids = [p['id'] for p in portfel_rows]
    xat_by_portfel = {}
    if portfel_ids:
        placeholders = ','.join('?' * len(portfel_ids))
        rows = conn.execute(f'''
            SELECT * FROM xatlar WHERE portfel_id IN ({placeholders})
              AND (arxivlangan IS NULL OR arxivlangan=0)
            ORDER BY id DESC
        ''', portfel_ids).fetchall()
        for r in rows:
            rd = dict(r)
            if rd['portfel_id'] not in xat_by_portfel:
                xat_by_portfel[rd['portfel_id']] = rd

    mib_amal_soni = {}
    mib_oxirgi_sana = {}
    xat_ids = [x['id'] for x in xat_by_portfel.values()]
    if xat_ids:
        placeholders2 = ','.join('?' * len(xat_ids))
        rows2 = conn.execute(f'''
            SELECT xat_id, COUNT(*) c, MAX(amal_sanasi) oxirgi FROM mib_amallar
            WHERE xat_id IN ({placeholders2}) GROUP BY xat_id
        ''', xat_ids).fetchall()
        for r in rows2:
            mib_amal_soni[r['xat_id']] = r['c']
            mib_oxirgi_sana[r['xat_id']] = r['oxirgi']
    conn.close()

    settings = get_all_settings()
    natija = []

    for prow in portfel_rows:
        if prow.get('anketa_raqami') in vafot_anketalar:
            continue  # Vafot etganlarga bu yerda ham chora ko'rilmaydi

        xat = xat_by_portfel.get(prow['id'])
        bosqich = 'xat_kerak'
        tafsilot = "Hali xat (Ogohlantirish/Talabnoma) yaratilmagan"
        qoshimcha = {}

        if not xat:
            pass
        elif xat.get('holat') not in ('yuborildi', 'muddati_otgan') or not xat.get('yuborilgan_sana'):
            bosqich = 'xat_yuborish_kerak'
            tafsilot = "Xat tayyor, lekin hali yuborilmagan"
        elif not xat.get('davo_ariza_fayl_yoli'):
            bosqich = 'davo_ariza_kerak'
            tafsilot = "Xat yuborilgan — Davo ariza tayyorlash kerak"
        elif xat.get('davo_ariza_holati') != 'olib_kelindi':
            bosqich = 'palata_kutilmoqda'
            tafsilot = "Davo ariza Palataga topshirilgan, javob kutilmoqda"
        elif xat.get('sud_holati') != 'topshirildi':
            bosqich = 'sud_kerak'
            tafsilot = "Palatadan qaytgan — sudga topshirish kerak"
        elif xat.get('mib_holati') != 'otkazildi':
            bosqich = 'mib_kerak'
            tafsilot = "Sudga topshirilgan — MIBga o'tkazish kerak"
        else:
            bosqich = 'mib_jarayonida'
            amal_soni = mib_amal_soni.get(xat['id'], 0)
            oxirgi_sana = mib_oxirgi_sana.get(xat['id'])
            jild_bor = xat.get('yigma_jild_holati') == 'mavjud'
            if amal_soni == 0:
                tafsilot = "MIBga o'tkazilgan, lekin hali birorta harakat qilinmagan"
            else:
                tafsilot = f"MIBda faol, so'nggi harakat: {oxirgi_sana or '—'}"
            qoshimcha['yigma_jild'] = jild_bor
            qoshimcha['mib_amal_soni'] = amal_soni
            nazorat = get_mib_monitoring_holati(xat['id'], prow, xat, settings)
            qoshimcha['nazorat_holati'] = nazorat.get('holat')
            qoshimcha['nazorat_xabar'] = nazorat.get('xabar')

        natija.append({
            'portfel': prow,
            'xat': xat,
            'bosqich': bosqich,
            'tafsilot': tafsilot,
            **qoshimcha,
        })

    tartib = {'xat_kerak': 0, 'xat_yuborish_kerak': 1, 'davo_ariza_kerak': 2,
              'sud_kerak': 3, 'mib_kerak': 4, 'palata_kutilmoqda': 5, 'mib_jarayonida': 6}
    natija.sort(key=lambda r: (tartib.get(r['bosqich'], 9), -(r['portfel'].get('balans_95413') or 0)))
    return natija


BOSQICH_NOMLARI_95413 = {
    'xat_kerak': "Xat yuborilishi kerak",
    'xat_yuborish_kerak': "Xat yuborilishi kerak (tayyor, yuborilmagan)",
    'davo_ariza_kerak': "Davo ariza tayyorlash kerak",
    'palata_kutilmoqda': "Palatadan javob kutilmoqda",
    'sud_kerak': "Sudga topshirish kerak",
    'mib_kerak': "MIBga o'tkazish kerak",
    'mib_jarayonida': "MIBda jarayonda",
}


def get_chora_korish_royxati():
    """
    Muddati o'tgan (DPD) kunlariga va joriy bosqichga qarab, har bir
    qoniqarsiz mijoz uchun qanday chora ko'rilishi kerakligini avtomatik
    aniqlaydi:
      1) DPD 50+ kun, so'nggi 2 oyda xat yuborilmagan -> xat yuborish kerak
      2) DPD 60+ kun (sud/MIB jarayonida bo'lmasa):
         - so'nggi 1 oyda xat yuborilgan -> Davo ariza tayyorlash kerak
         - yuborilmagan -> avval xat yuborish kerak
      3) MIBga o'tkazilgan, lekin hali birorta harakat qilinmagan
         -> ijro harakatlarini boshlash kerak
    """
    settings = get_all_settings()
    # MUHIM: 'dpd_chegara_kun' — Sozlamalarda foydalanuvchi ko'radigan va
    # o'zgartira oladigan YAGONA DPD chegarasi. Ilgari bu yerda alohida,
    # ekranda ko'rinmaydigan 'chora_ogohlantirish_dpd_kun' ishlatilar edi
    # (foydalanuvchi Sozlamada o'zgartirsa ham ta'sir qilmasdi) — endi
    # ikkalasi BIR XIL, ko'rinadigan qiymatga bog'landi.
    dpd_ogoh = int(settings.get('dpd_chegara_kun', settings.get('chora_ogohlantirish_dpd_kun', 45)))
    oy_ogoh = int(settings.get('chora_ogohlantirish_oy', 2))
    dpd_davo = int(settings.get('chora_davo_ariza_dpd_kun', 60))
    oy_davo = int(settings.get('chora_davo_ariza_oy', 1))
    # "Sudga kiritilmadi" deb belgilangan ishlar uchun: necha kundan keyin
    # qarzdorlik holatini qayta tekshirish kerak, va Davo arizaning
    # sudga topshirish uchun "amal qilish muddati" (qonun bo'yicha,
    # Fuqarolik sudi uchun 2 oy, Iqtisodiy sud uchun 15 kun — sozlanadi)
    # — shundan keyin butun jarayon qaytadan (noldan) boshlanishi
    # tavsiya etiladi.
    kiritilmadi_qayta_tekshirish_kun = int(settings.get('sud_kiritilmadi_qayta_tekshirish_kun', 30))
    davo_muddati_fuqarolik_kun = int(settings.get('davo_ariza_muddati_fuqarolik_kun', 60))   # 2 oy
    davo_muddati_iqtisodiy_kun = int(settings.get('davo_ariza_muddati_iqtisodiy_kun', 15))   # 15 kun

    now = datetime.datetime.now()
    portfel_rows = get_portfel_45_kun(dpd_ogoh)
    natija = []

    # Barcha kerakli xatlar va MIB harakat sonlarini BITTA so'rov bilan olib,
    # keyingi tsiklda qayta-qayta baza so'rovi qilmaslik uchun keshlaymiz.
    conn = get_conn()
    portfel_ids = [p['id'] for p in portfel_rows]
    xat_by_portfel = {}
    if portfel_ids:
        placeholders = ','.join('?' * len(portfel_ids))
        rows = conn.execute(f'''
            SELECT * FROM xatlar WHERE portfel_id IN ({placeholders})
              AND (arxivlangan IS NULL OR arxivlangan=0)
            ORDER BY id DESC
        ''', portfel_ids).fetchall()
        for r in rows:
            rd = dict(r)
            # Har bir portfel_id uchun eng oxirgi (id bo'yicha eng katta) xatni saqlaymiz
            if rd['portfel_id'] not in xat_by_portfel:
                xat_by_portfel[rd['portfel_id']] = rd

    mib_amal_soni = {}
    xat_ids = [x['id'] for x in xat_by_portfel.values()]
    if xat_ids:
        placeholders2 = ','.join('?' * len(xat_ids))
        rows2 = conn.execute(f'''
            SELECT xat_id, COUNT(*) c FROM mib_amallar
            WHERE xat_id IN ({placeholders2}) GROUP BY xat_id
        ''', xat_ids).fetchall()
        mib_amal_soni = {r['xat_id']: r['c'] for r in rows2}

    # Vafot etgan mijozlar (anketa raqami bo'yicha) — bularga hech qanday
    # chora ko'rilmaydi, sug'urta jarayoni alohida "Vafot etganlar" bo'limida
    # kuzatib boriladi.
    vafot_anketalar = {r['anketa_raqami'] for r in conn.execute(
        'SELECT DISTINCT anketa_raqami FROM vafot_etganlar').fetchall()}
    conn.close()

    for prow in portfel_rows:
        if prow.get('anketa_raqami') in vafot_anketalar:
            continue
        dpd = prow.get('dpd_max', 0)
        xat = xat_by_portfel.get(prow['id'])

        action = None
        detail = ''

        def xat_yuborilgan_kun_oldin():
            if xat and xat.get('yuborilgan_sana'):
                try:
                    yub_dt = datetime.datetime.fromisoformat(xat['yuborilgan_sana'])
                    return (now - yub_dt).days
                except (ValueError, TypeError, AttributeError):
                    return None
            return None

        jami_qarz_joriy = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        # MUHIM: agar MIB ishi allaqachon "yakunlangan" deb belgilangan
        # bo'lsa-yu, LEKIN bugungi kunda hali ham qarzdorlik mavjud bo'lsa
        # (masalan yakunlash sababi to'liq to'lov emas, balki boshqa sabab
        # bo'lgan) — bu, aslida, jarayon YANGIDAN, noldan boshlanishi
        # kerakligini bildiradi. Shu holatda, eski sud/Davo ariza
        # holatlariga qaramasdan, DPD asosida QAYTADAN baholaymiz.
        mib_qayta_boshlash_kerak = bool(
            xat and xat.get('mib_yakunlangan') and jami_qarz_joriy > 1
        )

        if xat and xat.get('mib_holati') == 'otkazildi' and not xat.get('mib_yakunlangan'):
            if mib_amal_soni.get(xat['id'], 0) == 0:
                action = 'mib_harakat_boshlash'
                detail = "MIBga o'tkazilgan, lekin hali birorta ijro harakati qayd qilinmagan"

        elif mib_qayta_boshlash_kerak:
            if dpd > dpd_davo:
                kun_oldin = xat_yuborilgan_kun_oldin()
                if kun_oldin is not None and kun_oldin <= oy_davo * 30:
                    action = 'davo_ariza_tayyorlash'
                    detail = "MIB yakunlangan, lekin qarz hali mavjud — jarayon qaytadan (Davo ariza) boshlanadi"
                else:
                    action = 'xat_yuborish_keyingi_bosqich'
                    detail = "MIB yakunlangan, lekin qarz hali mavjud — jarayon qaytadan (xat) boshlanadi"
            elif dpd > dpd_ogoh:
                action = 'xat_yuborish'
                detail = "MIB yakunlangan, lekin qarz hali mavjud — jarayon qaytadan (xat) boshlanadi"

        elif xat and xat.get('sud_holati') == 'topshirildi':
            pass  # Sud bazasida o'z nazorati bor, bu yerda chora talab qilinmaydi

        elif xat and xat.get('sud_kiritilmadi_sababi'):
            # "Sudga kiritilmadi" deb belgilangan ish. Belgilangan sanadan
            # necha kun o'tganini tekshiramiz.
            kun_oldin_kiritilmadi = None
            if xat.get('sud_kiritilmadi_sana'):
                try:
                    kd = datetime.datetime.strptime(xat['sud_kiritilmadi_sana'], '%d.%m.%Y')
                    kun_oldin_kiritilmadi = (now.date() - kd.date()).days
                except Exception:
                    kun_oldin_kiritilmadi = None

            if kun_oldin_kiritilmadi is None or kun_oldin_kiritilmadi < kiritilmadi_qayta_tekshirish_kun:
                pass  # Hali kutish muddati tugamagan
            elif jami_qarz_joriy <= 1:
                pass  # Qarz shu orada yopilgan — chora kerak emas
            else:
                # Belgilangan muddat o'tdi, LEKIN qarzdorlikda o'zgarish
                # yo'q (yopilmagan) — Davo arizaning "amal qilish muddati"
                # hali tugamaganmi tekshiramiz. Muddat sud turiga qarab
                # farqlanadi: Fuqarolik sudi (jismoniy) — 2 oy,
                # Iqtisodiy sud (yuridik/YaTT) — 15 kun.
                mijoz_turi_hisob = _turi_portfel_qatoridan(prow)
                muddat_shu_mijoz_uchun = (davo_muddati_iqtisodiy_kun
                                           if mijoz_turi_hisob in ('yuridik', 'yatt')
                                           else davo_muddati_fuqarolik_kun)
                davo_muddati_otganmi = True
                if xat.get('davo_ariza_imzo_sana'):
                    try:
                        imzo_dt = datetime.datetime.strptime(xat['davo_ariza_imzo_sana'], '%d.%m.%Y')
                        kun_imzodan = (now.date() - imzo_dt.date()).days
                        davo_muddati_otganmi = kun_imzodan > muddat_shu_mijoz_uchun
                    except Exception:
                        davo_muddati_otganmi = True

                if not davo_muddati_otganmi:
                    action = 'sudga_kiritish_kerak'
                    detail = (f"'Sudga kiritilmadi' belgilangandan {kun_oldin_kiritilmadi} kun o'tdi, "
                              f"qarzdorlik hamon mavjud — Davo ariza muddati hali amalda, "
                              f"to'xtatilgan joydan davom etib, sudga kiritish kerak")
                else:
                    action = 'jarayon_qaytadan_tiklash_kerak'
                    detail = (f"'Sudga kiritilmadi' belgilangandan {kun_oldin_kiritilmadi} kun o'tdi, "
                              f"qarzdorlik hamon mavjud, Davo arizaning amal qilish muddati "
                              f"({muddat_shu_mijoz_uchun} kun) tugagan — jarayonni "
                              f"noldan (nollashtirib) qayta boshlash kerak")

        elif xat and xat.get('davo_ariza_holati') == 'olib_kelindi':
            action = 'sudga_kiritish_kerak'
            detail = "Davo ariza SSPdan (Palatadan) tasdiqlanib qaytgan — sudga kiritish kerak"

        elif xat and xat.get('davo_ariza_fayl_yoli'):
            pass  # Davo ariza allaqachon tayyorlangan, SSP javobini
                  # kutilmoqda — bu "Davo Ariza" bo'limida kuzatiladi, qayta
                  # tayyorlash tavsiya qilinmasligi kerak.

        elif dpd > dpd_davo:
            kun_oldin = xat_yuborilgan_kun_oldin()
            if kun_oldin is not None and kun_oldin <= oy_davo * 30:
                action = 'davo_ariza_tayyorlash'
                detail = f"Xat {kun_oldin} kun oldin yuborilgan — Davo ariza tayyorlash vaqti keldi"
            else:
                action = 'xat_yuborish_keyingi_bosqich'
                detail = (f"DPD {dpd} kun, so'nggi {oy_davo} oyda xat yuborilmagan"
                          if kun_oldin is None else
                          f"Oxirgi xat {kun_oldin} kun oldin yuborilgan — eskirgan")

        elif dpd > dpd_ogoh:
            kun_oldin = xat_yuborilgan_kun_oldin()
            if kun_oldin is None or kun_oldin > oy_ogoh * 30:
                action = 'xat_yuborish'
                detail = (f"So'nggi {oy_ogoh} oyda xat yuborilmagan" if kun_oldin is None
                           else f"Oxirgi xat {kun_oldin} kun oldin yuborilgan — muddati o'tgan")

        if action:
            natija.append({
                'portfel': prow,
                'xat': xat,
                'dpd': dpd,
                'turi': _turi_portfel_qatoridan(prow),
                'chora': action,
                'chora_nomi': CHORA_NOMLARI.get(action, action),
                'tafsilot': detail,
            })

    # Eng shoshilinch choralar (MIB, Davo ariza) tepada ko'rinishi uchun tartiblash
    tartib = {'mib_harakat_boshlash': 0, 'davo_ariza_tayyorlash': 1,
              'xat_yuborish_keyingi_bosqich': 2, 'xat_yuborish': 3}
    natija.sort(key=lambda r: (tartib.get(r['chora'], 9), -r['dpd']))
    return natija


def get_mijoz_holati_anketa_boyicha(anketa_raqami):
    """
    Anketa raqami bo'yicha butun portfelda qidirib, topilgan har bir kredit
    uchun mijozning qaysi bosqichda ekanini (xat/davo ariza/sud/MIB) to'liq
    ko'rsatuvchi ma'lumot qaytaradi.
    """
    portfel_rows = get_portfel_by_anketa(anketa_raqami)
    natija = []
    for prow in portfel_rows:
        conn = get_conn()
        xat = conn.execute('SELECT * FROM xatlar WHERE portfel_id=? '
                            'ORDER BY id DESC LIMIT 1', (prow['id'],)).fetchone()
        conn.close()
        item = {'portfel': prow, 'xat': dict(xat) if xat else None, 'oxirgi_mib_amal': None}
        if xat and dict(xat).get('mib_holati') == 'otkazildi':
            amallar = get_mib_amallar(xat['id'])
            if amallar:
                item['oxirgi_mib_amal'] = amallar[0]
        natija.append(item)
    return natija


def get_olib_kelinganlar_royxati():
    """
    Palatadan/imzodan qaytgan ("olib_kelindi") barcha Davo arizalar
    ro'yxatini, davo summasi farqi va boshqa tafsilotlar bilan qaytaradi
    (Excel eksporti uchun).
    """
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar
        WHERE davo_ariza_holati='olib_kelindi'
        ORDER BY davo_ariza_imzo_sana DESC
    ''').fetchall()
    conn.close()
    settings = get_all_settings()

    natija = []
    for r in rows:
        rd = dict(r)
        prow = get_portfel_by_id(rd['portfel_id'])
        farqi = get_davo_ariza_farqi(rd, prow, settings) if prow else {
            'davo_summasi': 0, 'davo_summasi_asosiy': 0, 'davo_summasi_foiz': 0,
            'davo_summasi_jarima': 0, 'joriy_qarz': 0, 'farq': 0, 'qoshimcha_kerak': False,
        }
        natija.append({
            'xat': rd, 'portfel': prow,
            'pinfl': (prow.get('pinfl') if prow else '') or '',
            **farqi,
        })
    return natija


def get_sud_hisoboti():
    """Sudga topshirilgan barcha hujjatlar bo'yicha to'liq hisobot."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar
        WHERE davo_ariza_holati='olib_kelindi'
        ORDER BY davo_ariza_imzo_sana DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_davo_ariza_hisoboti():
    """Davo ariza tayyorlangan barcha mijozlar bo'yicha to'liq hisobot."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar
        WHERE davo_ariza_fayl_yoli IS NOT NULL AND davo_ariza_fayl_yoli != ''
        ORDER BY davo_ariza_sana DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_taminot(anketa_raqami):
    conn = get_conn()
    row = conn.execute('SELECT * FROM davo_taminot WHERE anketa_raqami=?', (anketa_raqami,)).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_taminot(anketa_raqami, **fields):
    conn = get_conn()
    now = datetime.datetime.now().isoformat()
    existing = conn.execute('SELECT anketa_raqami FROM davo_taminot WHERE anketa_raqami=?',
                             (anketa_raqami,)).fetchone()
    cols = ['taminot_turi', 'kafil_ism', 'kafil_manzil', 'kafil_pinfl', 'kafil_passport',
            'kafil_passport_sana', 'kafil_passport_organ', 'kafil_tel', 'garov_tavsifi',
            'garov_bahosi', 'pochta_xarajati']
    values = {c: fields.get(c, '') for c in cols}
    if existing:
        set_clause = ', '.join(f'{c}=?' for c in cols)
        conn.execute(f'UPDATE davo_taminot SET {set_clause}, yangilangan_sana=? WHERE anketa_raqami=?',
                     [values[c] for c in cols] + [now, anketa_raqami])
    else:
        all_cols = ['anketa_raqami'] + cols + ['yangilangan_sana']
        placeholders = ','.join(['?'] * len(all_cols))
        conn.execute(f'INSERT INTO davo_taminot ({",".join(all_cols)}) VALUES ({placeholders})',
                     [anketa_raqami] + [values[c] for c in cols] + [now])
    conn.commit()
    conn.close()


def bulk_upsert_taminot(records):
    """records: list of dicts with 'anketa_raqami' + the davo_taminot fields."""
    conn = get_conn()
    now = datetime.datetime.now().isoformat()
    cols = ['taminot_turi', 'kafil_ism', 'kafil_manzil', 'kafil_pinfl', 'kafil_passport',
            'kafil_passport_sana', 'kafil_passport_organ', 'kafil_tel', 'garov_tavsifi',
            'garov_bahosi', 'pochta_xarajati']
    all_cols = ['anketa_raqami'] + cols + ['yangilangan_sana']
    placeholders = ','.join(['?'] * len(all_cols))
    set_clause = ', '.join(f'{c}=excluded.{c}' for c in cols)
    sql = f'''INSERT INTO davo_taminot ({",".join(all_cols)}) VALUES ({placeholders})
              ON CONFLICT(anketa_raqami) DO UPDATE SET {set_clause}, yangilangan_sana=excluded.yangilangan_sana'''
    rows = []
    for r in records:
        rows.append([r.get('anketa_raqami')] + [r.get(c, '') for c in cols] + [now])
    conn.executemany(sql, rows)
    conn.commit()
    conn.close()


def get_xatlar_yuborilgan_davo_kerak():
    """'Yuborildi' holatidagi barcha xatlar — Davo Ariza ekranining to'liq
    tarixiy ro'yxati uchun (MIB bosqichiga o'tganlar ham shu yerda,
    tegishli holat matni bilan ko'rsatiladi)."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar WHERE holat='yuborildi'
        ORDER BY yuborilgan_sana DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_xat_by_id(xat_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE id=?', (xat_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_muddati_otganlar():
    """3 kunlik muddat o'tgan, lekin hali yuborilmagan xatlarni belgilaydi."""
    conn = get_conn()
    now = datetime.datetime.now().isoformat()
    conn.execute('''
        UPDATE xatlar SET holat='muddati_otgan'
        WHERE holat='tayyor' AND muddat_sana < ?
    ''', (now,))
    conn.commit()
    n = conn.execute("SELECT COUNT(*) c FROM xatlar WHERE holat='muddati_otgan'").fetchone()['c']
    conn.close()
    return n


def get_davo_ariza_muddati_otganlar(muddat_kun=None):
    """
    Davo ariza tayyorlangan (yaratilgan), lekin belgilangan muddat ichida
    (standart 5 kun) hali 'olib kelindi' deb belgilanmagan mijozlar ro'yxati.
    """
    if muddat_kun is None:
        muddat_kun = int(get_setting('davo_ariza_muddati_kun', 5))
    chegara = (datetime.datetime.now() - datetime.timedelta(days=muddat_kun)).isoformat()
    conn = get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar
        WHERE davo_ariza_fayl_yoli IS NOT NULL AND davo_ariza_fayl_yoli != ''
          AND (davo_ariza_holati IS NULL OR davo_ariza_holati != 'olib_kelindi')
          AND davo_ariza_sana < ?
        ORDER BY davo_ariza_sana ASC
    ''', (chegara,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
