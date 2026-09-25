# -*- coding: utf-8 -*-
"""
Excel/XLSB fayllardan ma'lumot import qilish.
"""
import pandas as pd
import database as db
import util

# Portfel faylidagi ustun nomlari -> bazamizdagi maydon nomlari
PORTFEL_COLMAP = {
    'Порт_код': 'port_kod',
    'Анкета раками': 'anketa_raqami',
    'Уникал': 'unikal',
    'СТИР': 'stir',
    'ПИНФЛ': 'pinfl',
    'Филиал коди': 'filial_kodi',
    'Вилоят': 'viloyat',
    'Тармок': 'tarmoq',
    'Stage': 'stage',
    'Жис / юр / Ятт - коди': 'mijoz_turi_kodi',
    'Мижоз тури': 'mijoz_turi',
    'Мижоз номи': 'mijoz_nomi',
    'Валюта коди': 'valyuta',
    'Кредит хисоб раками': 'kredit_hisob_raqami',
    'Йиллик фоиз ставкаси': 'yillik_foiz',
    'Шартнома санаси': 'shartnoma_sanasi',
    'Шартнома тугаш санаси': 'shartnoma_tugash_sanasi',
    'Тулов максади': 'tulov_maqsadi',
    'DPD days of principal -Муддати ўтган асосий қарз кунлар сони': 'dpd_asosiy',
    'DPD days of percentage -Муддати ўтган фоиз кунлар сони': 'dpd_foiz',
    'EAD (Жами қарздорлик суммаси)': 'ead',
    'Муддати утган жами кредит колдиги (экв)': 'asosiy_qarz',
    'Жами 16300 колдиғи': 'foiz_qarz',
    'Колдик 16405': 'jarima',
    'Колдик 95413': 'balans_95413',
}


def _clean_id(val):
    """Raqamli ID maydonlarini (СТИР, ПИНФЛ, Уникал...) '123.0' emas '123' ko'rinishga keltiradi."""
    if val is None:
        return None
    try:
        import math
        if isinstance(val, float):
            if math.isnan(val):
                return None
            if val == int(val):
                return str(int(val))
            return str(val)
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s if s and s.lower() != 'nan' else None


ID_FIELDS = {'anketa_raqami', 'unikal', 'stir', 'pinfl', 'filial_kodi', 'kredit_hisob_raqami'}


def import_portfel_xlsb(filepath, sheet_name=None, progress_cb=None):
    """
    Portfel .xlsb faylini o'qib, bazaga yozadi.
    sheet_name berilmasa, ma'lumot bor birinchi varaq olinadi.
    """
    xl = pd.ExcelFile(filepath, engine='pyxlsb')
    sheets = xl.sheet_names

    df = None
    chosen_sheet = None
    if sheet_name:
        df = pd.read_excel(filepath, engine='pyxlsb', sheet_name=sheet_name)
        chosen_sheet = sheet_name
    else:
        for s in sheets:
            tmp = pd.read_excel(filepath, engine='pyxlsb', sheet_name=s)
            if len(tmp) > 0:
                df = tmp
                chosen_sheet = s
                break
        if df is None:
            df = pd.read_excel(filepath, engine='pyxlsb', sheet_name=sheets[0])
            chosen_sheet = sheets[0]

    available_cols = {c: PORTFEL_COLMAP[c] for c in PORTFEL_COLMAP if c in df.columns}
    missing = [c for c in PORTFEL_COLMAP if c not in df.columns]

    rows = []
    total = len(df)
    for i, (_, r) in enumerate(df.iterrows()):
        row = {}
        for src_col, dst_field in available_cols.items():
            val = r.get(src_col)
            if dst_field in ID_FIELDS:
                val = _clean_id(val)
            if dst_field == 'mijoz_nomi':
                val = util.clean_mijoz_ism(val)
            row[dst_field] = val

        dpd_a = row.get('dpd_asosiy') or 0
        dpd_f = row.get('dpd_foiz') or 0
        try:
            dpd_a = int(dpd_a)
        except (TypeError, ValueError):
            dpd_a = 0
        try:
            dpd_f = int(dpd_f)
        except (TypeError, ValueError):
            dpd_f = 0
        row['dpd_asosiy'] = dpd_a
        row['dpd_foiz'] = dpd_f
        row['dpd_max'] = max(dpd_a, dpd_f)

        def to_float(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        asosiy = to_float(row.get('asosiy_qarz'))
        foiz = to_float(row.get('foiz_qarz'))
        jarima_v = to_float(row.get('jarima'))
        row['asosiy_qarz'] = asosiy
        row['foiz_qarz'] = foiz
        row['jarima'] = jarima_v
        row['jami_qarz'] = asosiy + foiz + jarima_v
        row['balans_95413'] = to_float(row.get('balans_95413'))

        rows.append(row)
        if progress_cb and i % 200 == 0:
            progress_cb(i, total)

    db.insert_portfel_rows(rows)
    return {
        'sheet': chosen_sheet,
        'jami_qator': len(rows),
        'topilmagan_ustunlar': missing,
    }


def preview_mijozlar_columns(filepath, sheet_name=0, nrows=5):
    """Mijozlar faylining ustunlarini va namuna qatorlarini qaytaradi (moslashtirish uchun)."""
    df = pd.read_excel(filepath, sheet_name=sheet_name, nrows=nrows)
    return list(df.columns), df.head(nrows)


def import_mijozlar_xlsx(filepath, turi, column_mapping, sheet_name=0, progress_cb=None):
    """
    turi: 'jismoniy' yoki 'yuridik'
    column_mapping: dict — {'kalit': 'Excel ustun nomi', 'ism': '...', 'manzil': '...',
                             'telefon': '...', 'hujjat_raqami': '...', 'rahbar_ism': '...'}
    Faqat 'kalit' va 'ism' majburiy — qolganlari bo'sh qoldirilishi mumkin.
    """
    df = pd.read_excel(filepath, sheet_name=sheet_name)
    total = len(df)
    count = 0
    for i, (_, r) in enumerate(df.iterrows()):
        def get(field):
            col = column_mapping.get(field)
            if not col or col not in df.columns:
                return ''
            val = r.get(col)
            if pd.isna(val):
                return ''
            return str(val).strip()

        kalit = get('kalit')
        ism = util.clean_mijoz_ism(get('ism'))
        if not kalit or not ism:
            continue
        db.upsert_mijoz(
            turi=turi,
            kalit=kalit,
            ism=ism,
            manzil=get('manzil'),
            telefon=_clean_id(get('telefon')) or get('telefon'),
            hujjat_raqami=get('hujjat_raqami'),
            rahbar_ism=get('rahbar_ism'),
        )
        count += 1
        if progress_cb and i % 200 == 0:
            progress_cb(i, total)

    return {'jami_qator': total, 'import_qilingan': count}


# ---------------------------------------------------------------------------
# Talabnoma ro'yxatini Excel'ga eksport qilish / tahrirlangan Excel'ni qaytarib olish
# ---------------------------------------------------------------------------

TAHLIL_EXPORT_COLS = [
    ('anketa_raqami', 'Anketa raqami'),
    ('mijoz_nomi', 'Mijoz nomi'),
    ('turi', 'Turi'),
    ('manzil', 'Manzil'),
    ('telefon', 'Telefon'),
    ('dpd_max', 'DPD (kun)'),
    ('jami_qarz', "Muddati o'tgan qarz"),
    ('jami_berilgan_summa', "Jami berilgan kredit summasi"),
    ('xat_turi', 'Xat turi'),
]


def export_tahlil_excel(rows, output_path):
    """
    rows: list of dict — har birida anketa_raqami, mijoz_nomi, turi, manzil,
          telefon, dpd_max, jami_qarz, xat_turi kalitlari bo'lishi kerak.
    Manzil va Telefon ustunlari tahrirlash uchun — qolganlari faqat ma'lumot uchun.
    """
    cols = [c[0] for c in TAHLIL_EXPORT_COLS]
    headers = [c[1] for c in TAHLIL_EXPORT_COLS]
    data = [[r.get(c, '') for c in cols] for r in rows]
    df = pd.DataFrame(data, columns=headers)
    df.to_excel(output_path, index=False)
    return output_path


def import_manzil_updates(filepath):
    """
    Tahrirlangan Excel'ni o'qib, 'Manzil' / 'Telefon' ustunlaridagi
    o'zgarishlarni mijozlar bazasiga, 'Jami berilgan kredit summasi'
    ustunidagi qiymatni esa portfelga (Anketa raqami orqali bog'lab) yozadi.
    """
    df = pd.read_excel(filepath)
    required = {'Anketa raqami', 'Manzil'}
    if not required.issubset(set(df.columns)):
        raise ValueError(
            "Excel faylida 'Anketa raqami' va 'Manzil' ustunlari topilmadi. "
            "Iltimos, dastur bergan asl Excel tuzilmasini o'zgartirmang."
        )
    has_summa_col = 'Jami berilgan kredit summasi' in df.columns

    updated = 0
    skipped = 0
    summa_yangilandi = 0
    for _, r in df.iterrows():
        anketa = r.get('Anketa raqami')
        if pd.isna(anketa):
            continue
        anketa = str(anketa).strip()
        yangi_manzil = r.get('Manzil')
        yangi_manzil = '' if pd.isna(yangi_manzil) else str(yangi_manzil).strip()
        yangi_telefon = _clean_id(r.get('Telefon')) or ''
        yangi_ism = r.get('Mijoz nomi')
        yangi_ism = None if pd.isna(yangi_ism) else str(yangi_ism).strip()

        portfel_rows = db.get_portfel_by_anketa(anketa)
        if not portfel_rows:
            skipped += 1
            continue
        prow = portfel_rows[0]
        turi, mijoz = util.resolve_mijoz(prow)

        if mijoz:
            kalit = mijoz['kalit']
            ism = yangi_ism or mijoz['ism']
            hujjat = mijoz.get('hujjat_raqami', '') or ''
            rahbar = mijoz.get('rahbar_ism', '') or ''
        else:
            kalit = next((k for k in util.kalit_candidates(prow) if k), None)
            if not kalit:
                skipped += 1
                continue
            ism = yangi_ism or prow.get('mijoz_nomi', '')
            hujjat = ''
            rahbar = ''

        db.upsert_mijoz(
            turi=turi, kalit=str(kalit), ism=ism, manzil=yangi_manzil,
            telefon=yangi_telefon, hujjat_raqami=hujjat, rahbar_ism=rahbar,
        )
        updated += 1

        if has_summa_col:
            yangi_summa = r.get('Jami berilgan kredit summasi')
            if not pd.isna(yangi_summa) and str(yangi_summa).strip() != '':
                try:
                    summa_qiymati = float(str(yangi_summa).replace(' ', '').replace(',', ''))
                    db.set_jami_berilgan_summa(prow['id'], summa_qiymati)
                    summa_yangilandi += 1
                except (ValueError, TypeError):
                    pass

    return {'yangilandi': updated, 'otkazib_yuborildi': skipped, 'summa_yangilandi': summa_yangilandi}


# ---------------------------------------------------------------------------
# Davo ariza uchun kafil/garov (ta'minot) ma'lumotlarini Excel orqali
# tekshirish/tahrirlash
# ---------------------------------------------------------------------------

TAMINOT_EXPORT_COLS = [
    ('anketa_raqami', 'Anketa raqami'),
    ('mijoz_nomi', 'Mijoz nomi'),
    ('taminot_turi', "Ta'minot turi (yoq/kafillik/garov/kafillik_garov)"),
    ('kafil_ism', 'Kafil F.I.Sh'),
    ('kafil_manzil', 'Kafil manzili'),
    ('kafil_pinfl', 'Kafil PINFL'),
    ('kafil_passport', 'Kafil passport (seriya-raqam)'),
    ('kafil_passport_sana', 'Kafil passport berilgan sana'),
    ('kafil_passport_organ', 'Kafil passport bergan organ'),
    ('kafil_tel', 'Kafil telefon'),
    ('garov_tavsifi', "Garov mulki tavsifi"),
    ('garov_bahosi', 'Garov bahosi (som)'),
    ('pochta_xarajati', "Pochta xarajati (som, bo'sh bo'lsa standart qiymat ishlatiladi)"),
]


def export_taminot_excel(rows, output_path):
    """
    rows: list of dict — anketa_raqami, mijoz_nomi va davo_taminot maydonlari
          (mavjud bo'lsa joriy qiymatlar bilan, bo'lmasa bo'sh).
    """
    cols = [c[0] for c in TAMINOT_EXPORT_COLS]
    headers = [c[1] for c in TAMINOT_EXPORT_COLS]
    data = [[r.get(c, '') for c in cols] for r in rows]
    df = pd.DataFrame(data, columns=headers)
    df.to_excel(output_path, index=False)
    return output_path


def import_taminot_excel(filepath):
    """Tahrirlangan ta'minot Excel faylini o'qib, bazaga (davo_taminot) yozadi.

    MUHIM: "Ta'minot turi" ustunini foydalanuvchi to'g'ri to'ldirmasligi
    (yoki umuman bo'sh qoldirishi) mumkin — masalan Kafil F.I.Sh yoki
    Garov mulki tavsifini to'ldirib, lekin turi ustunini yozishni unutib
    qo'yishi. Shu sabab taminot_turi HAR DOIM kafil/garov maydonlarining
    haqiqatda to'ldirilgan-to'ldirilmaganligidan avtomatik aniqlanadi —
    Excel'dagi "Ta'minot turi" ustuniga endi umuman tayanilmaydi, shunda
    Davo ariza turi tanlashda xato bo'lmaydi.
    """
    df = pd.read_excel(filepath)
    col_map = {c[1]: c[0] for c in TAMINOT_EXPORT_COLS}
    missing = [h for h in ['Anketa raqami'] if h not in df.columns]
    if missing:
        raise ValueError(f"Excel faylida quyidagi ustunlar topilmadi: {missing}")

    records = []
    for _, r in df.iterrows():
        anketa = r.get('Anketa raqami')
        if pd.isna(anketa):
            continue
        rec = {'anketa_raqami': str(anketa).strip()}
        for header, field in col_map.items():
            if field in ('anketa_raqami', 'mijoz_nomi'):
                continue
            val = r.get(header)
            if pd.isna(val):
                val = ''
            else:
                val = str(val).strip() if field != 'garov_bahosi' and field != 'pochta_xarajati' else val
            rec[field] = val

        # taminot_turi'ni AVTOMATIK aniqlaymiz — Excel ustunidagi qiymatga
        # emas, balki kafil_ism/garov_tavsifi haqiqatda to'ldirilganiga qarab
        kafil_bor = bool(str(rec.get('kafil_ism') or '').strip())
        garov_bor = bool(str(rec.get('garov_tavsifi') or '').strip())
        if kafil_bor and garov_bor:
            rec['taminot_turi'] = 'kafillik_garov'
        elif kafil_bor:
            rec['taminot_turi'] = 'kafillik'
        elif garov_bor:
            rec['taminot_turi'] = 'garov'
        else:
            # Kafil/garov maydonlari bo'sh — foydalanuvchi Excel'da aniq
            # to'g'ri qiymat yozgan bo'lishi mumkin (masalan faqat "garov"
            # deb, tavsifini boshqa joyda saqlagan) — shu holda uni
            # hurmat qilamiz, aks holda "yo'q" deb qoldiramiz.
            mavjud_qiymat = str(rec.get('taminot_turi') or '').strip().lower()
            if mavjud_qiymat in ('kafillik', 'garov', 'kafillik_garov'):
                rec['taminot_turi'] = mavjud_qiymat
            else:
                rec['taminot_turi'] = 'yoq'

        records.append(rec)

    db.bulk_upsert_taminot(records)
    return {'yangilandi': len(records)}


# ---------------------------------------------------------------------------
# Avtomashinalarni Excel orqali ommaviy import qilish (MIB bosqichi uchun)
# ---------------------------------------------------------------------------

def import_avtomashinalar_excel(filepath):
    """
    Excel faylidan avtomashinalar ro'yxatini o'qib, har bir qatorni
    'Anketa raqami' (birinchi navbatda) yoki 'Mijoz PINFL' orqali tegishli
    MIB ishiga (xat_id) avtomatik bog'lab, bazaga qo'shadi.

    Kerakli ustunlar: 'Mashina rusumi', 'Davlat raqami', va kamida bittasi:
    'Anketa raqami' yoki 'Mijoz PINFL'.

    Faqat MIBga o'tkazilgan ('mib_holati'='otkazildi') ishlarga bog'lanadi —
    aks holda qaysi ishga tegishli ekanini aniq bilib bo'lmaydi.
    """
    df = pd.read_excel(filepath)
    cols_lower = {c.strip().lower(): c for c in df.columns}

    def topilgan_ustun(*nomlar):
        for n in nomlar:
            if n.lower() in cols_lower:
                return cols_lower[n.lower()]
        return None

    rusumi_col = topilgan_ustun('Mashina rusumi')
    davlat_col = topilgan_ustun('Davlat raqami')
    anketa_col = topilgan_ustun('Anketa raqami')
    pinfl_col = topilgan_ustun('Mijoz PINFL', 'PINFL')

    if not rusumi_col or not davlat_col:
        raise ValueError("Excel faylida 'Mashina rusumi' va 'Davlat raqami' ustunlari topilmadi.")
    if not anketa_col and not pinfl_col:
        raise ValueError("Excel faylida 'Anketa raqami' yoki 'Mijoz PINFL' ustunlaridan "
                          "kamida bittasi bo'lishi shart (mijozni aniqlash uchun).")

    conn = db.get_conn()
    qoshildi, topilmadi, xato = 0, [], []

    for _, r in df.iterrows():
        rusumi = r.get(rusumi_col)
        davlat_raqami = r.get(davlat_col)
        if pd.isna(rusumi) or pd.isna(davlat_raqami):
            continue
        rusumi = str(rusumi).strip()
        davlat_raqami = str(davlat_raqami).strip()

        anketa = None
        if anketa_col:
            v = r.get(anketa_col)
            anketa = None if pd.isna(v) else _clean_id(v)
        pinfl = None
        if pinfl_col:
            v = r.get(pinfl_col)
            pinfl = None if pd.isna(v) else _clean_id(str(v))

        xat_row = None
        if anketa:
            xat_row = conn.execute('''
                SELECT x.* FROM xatlar x
                WHERE x.anketa_raqami=? AND x.mib_holati='otkazildi'
                ORDER BY x.id DESC LIMIT 1
            ''', (anketa,)).fetchone()
        if not xat_row and pinfl:
            xat_row = conn.execute('''
                SELECT x.* FROM xatlar x
                JOIN portfel p ON p.id = x.portfel_id
                WHERE p.pinfl=? AND x.mib_holati='otkazildi'
                ORDER BY x.id DESC LIMIT 1
            ''', (pinfl,)).fetchone()

        if not xat_row:
            topilmadi.append({'rusumi': rusumi, 'davlat_raqami': davlat_raqami,
                               'anketa': anketa, 'pinfl': pinfl})
            continue

        mijoz_pinfl = pinfl or ''
        if not mijoz_pinfl:
            prow = conn.execute('SELECT pinfl FROM portfel WHERE id=?',
                                 (xat_row['portfel_id'],)).fetchone()
            mijoz_pinfl = (prow['pinfl'] if prow else '') or ''

        db.add_avtomashina(xat_row['id'], rusumi, davlat_raqami, mijoz_pinfl)
        qoshildi += 1

    conn.close()
    return {'qoshildi': qoshildi, 'topilmadi': topilmadi}


# ---------------------------------------------------------------------------
# Mijozlar bazasini xom matn (.txt yoki .zip) fayldan import qilish
# Bu format Excel orqali buzilmagan, aniq | bilan ajratilgan asl eksport.
# ---------------------------------------------------------------------------

def _norm_id(v):
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    # Butunlay nollardan iborat qiymat ("0", "000...0") — bu haqiqiy
    # identifikator emas, balki bank fayllaridagi bo'sh/placeholder
    # yozuv. Bunday qiymatni kalit sifatida ishlatib bo'lmaydi — aks
    # holda turli mijozlar bir-biriga tasodifan bog'lanib qolishi mumkin.
    if v.strip('0') == '':
        return None
    stripped = v.lstrip('0')
    return stripped if stripped else v


def _open_client_text(filepath):
    """.txt yoki .zip (ichida bitta .txt) faylni ochib, matn qatorlarini beradi."""
    import zipfile
    if filepath.lower().endswith('.zip'):
        zf = zipfile.ZipFile(filepath)
        names = [n for n in zf.namelist() if not n.endswith('/')]
        if not names:
            raise ValueError("Zip fayl ichida hech narsa topilmadi.")
        raw = zf.read(names[0])
        zf.close()
        return raw.decode('cp1251', errors='replace').split('\r\n')
    else:
        with open(filepath, 'rb') as f:
            raw = f.read()
        return raw.decode('cp1251', errors='replace').split('\r\n')


def import_clients_txt(filepath, progress_cb=None):
    """
    Bank tizimidan olingan xom (| bilan ajratilgan) mijozlar faylini import qiladi.
    CODE_SUBJECT ustuniga qarab avtomatik jismoniy/yuridik ekanini aniqlaydi.
    Har bir mijoz uchun bir nechta kalit (ID_CLIENT, STIR, PINFL) bilan saqlanadi —
    shunda portfel bilan bog'lash ehtimoli maksimal bo'ladi.
    """
    lines = _open_client_text(filepath)

    header_fields = None
    header_idx = None
    for i, l in enumerate(lines):
        if l.startswith('|ID'):
            header_fields = [h.strip() for h in l.split('|')]
            header_idx = i
            break
    if header_fields is None:
        raise ValueError("Fayl tuzilmasi tanilmadi — '|ID' bilan boshlanuvchi sarlavha topilmadi.")

    n_fields = len(header_fields)
    idx = {name: i for i, name in enumerate(header_fields)}

    def col(vals, name, default=''):
        i = idx.get(name)
        if i is None or i >= len(vals):
            return default
        return vals[i].strip()

    total = len(lines) - header_idx
    imported = 0
    skipped_rows = 0
    batch = []
    BATCH_SIZE = 5000

    def flush_batch():
        nonlocal batch
        if batch:
            db.bulk_upsert_mijozlar(batch)
            batch = []

    for line_no, l in enumerate(lines[header_idx + 2:]):
        if progress_cb and line_no % 2000 == 0:
            progress_cb(line_no, total)
        if not l.strip() or l.strip('-') == '':
            continue
        vals = l.split('|')
        if len(vals) != n_fields:
            skipped_rows += 1
            continue

        subj = col(vals, 'CODE_SUBJECT').upper()
        id_client = _norm_id(col(vals, 'ID_CLIENT'))
        passport_sana = ''
        passport_organ = ''

        if subj == 'J':
            turi = 'yuridik'
            ism = util.clean_mijoz_ism(col(vals, 'J_SHORT_NAME') or col(vals, 'NAME'))
            manzil = col(vals, 'J_POST_ADDRESS')
            telefon = col(vals, 'J_PHONE')
            rahbar = (col(vals, 'J_DIRECTOR_NAME') + ' ' + col(vals, 'J_DIRECTOR_FIRST_NAME')).strip()
            hujjat = col(vals, 'J_NUMBER_TAX_REGISTRATION')
            keys = [id_client, _norm_id(hujjat)]
        elif subj == 'P':
            turi = 'jismoniy'
            ism = util.clean_mijoz_ism(col(vals, 'NAME'))
            manzil = col(vals, 'P_POST_ADDRESS')
            telefon = col(vals, 'P_PHONE_MOBILE') or col(vals, 'P_PHONE_HOME')
            rahbar = ''
            hujjat = (col(vals, 'P_PASSPORT_SERIAL') + col(vals, 'P_PASSPORT_NUMBER')).strip()
            passport_sana = col(vals, 'P_PASSPORT_DATE_REGISTRATION')
            passport_organ = col(vals, 'P_PASSPORT_PLACE_REGISTRATION')
            pinfl = _norm_id(col(vals, 'P_PINFL'))
            keys = [id_client, pinfl]
        elif subj == 'I':
            turi = 'jismoniy'
            ism = util.clean_mijoz_ism(col(vals, 'I_SHORT_NAME') or col(vals, 'NAME'))
            manzil = col(vals, 'I_POST_ADDRESS')
            telefon = col(vals, 'I_PHONE')
            rahbar = (col(vals, 'I_DIRECTOR_NAME') + ' ' + col(vals, 'I_DIRECTOR_FIRST_NAME')).strip()
            hujjat = col(vals, 'I_NUMBER_TAX_REGISTRATION')
            keys = [id_client, _norm_id(hujjat)]
        else:
            skipped_rows += 1
            continue

        if not ism:
            skipped_rows += 1
            continue

        seen_here = set()
        wrote_any = False
        for k in keys:
            if not k or k in seen_here:
                continue
            seen_here.add(k)
            batch.append((turi, k, ism, manzil, telefon, hujjat, rahbar, passport_sana, passport_organ))
            wrote_any = True
        if wrote_any:
            imported += 1
        else:
            skipped_rows += 1

        if len(batch) >= BATCH_SIZE:
            flush_batch()

    flush_batch()
    return {'jami_qator': total, 'import_qilingan': imported, 'otkazib_yuborildi': skipped_rows}
