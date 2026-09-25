# -*- coding: utf-8 -*-
"""✏ tugmasi ishlashini tekshirish (prompt() o'rniga yangi dialog)."""
import asyncio, http.server, socketserver, threading, functools
from playwright.async_api import async_playwright
ROOT='/home/claude/qarz_nazorat_web/frontend'; PORT=8881
httpd=socketserver.TCPServer(("",PORT), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
threading.Thread(target=httpd.serve_forever, daemon=True).start()

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1500,'height':1000})
        pg.on('pageerror', lambda e: print('  [pe]', str(e)[:200]))
        # MUHIM: Electrondagi holatni taqlid qilamiz — prompt() ishlamasin
        await pg.add_init_script("window.prompt = () => { throw new Error('prompt Electronda ishlamaydi'); };")
        await pg.goto(f'http://127.0.0.1:{PORT}/index.html'); await pg.wait_for_timeout(500)
        await pg.evaluate("API_BASE='http://127.0.0.1:5001/api'"); await pg.wait_for_timeout(3000)

        await pg.click(".sb-item[data-key='biznes_hamroh']"); await pg.wait_for_timeout(2500)
        btn = await pg.query_selector('[data-bh-anketa]')
        if not btn:
            print("  ✗ portal ro'yxati bo'sh"); await b.close(); return
        await btn.click()
        await pg.wait_for_selector('#bh-modal .card', timeout=15000); await pg.wait_for_timeout(1200)

        # "Shartnoma raqami" maydonining ✏ tugmasi
        qalam = await pg.query_selector("[data-bh-tahrir='shartnoma_raqami']")
        if not qalam:
            print("  ✗ ✏ tugmasi topilmadi"); await b.close(); return
        eski = await pg.evaluate("document.querySelector(\"[data-bh-tahrir='shartnoma_raqami']\").dataset.bhJoriy")
        print(f"  joriy qiymat: {eski}")
        await qalam.click(); await pg.wait_for_timeout(700)

        dialog = await pg.query_selector('#ms-qiymat')
        if not dialog:
            print("  ✗ DIALOG OCHILMADI — ✏ hamon ishlamayapti"); await b.close(); return
        print("  ✓ dialog ochildi")
        await pg.screenshot(path='/tmp/claude-0/qalam_dialog.png')

        await pg.fill('#ms-qiymat', 'YANGI-RAQAM-12345')
        await pg.click('#ms-saqlash')
        await pg.wait_for_timeout(2500)

        yangi = await pg.evaluate("document.querySelector(\"[data-bh-tahrir='shartnoma_raqami']\").dataset.bhJoriy")
        print(f"  saqlangandan keyin: {yangi}")
        print("  ✓ QIYMAT O'ZGARDI" if yangi == 'YANGI-RAQAM-12345' else f"  ✗ o'zgarmadi")
        await pg.screenshot(path='/tmp/claude-0/qalam_natija.png')

        # Escape bilan bekor qilish ishlaydimi
        await qalam.click() if (qalam := await pg.query_selector("[data-bh-tahrir='shartnoma_raqami']")) else None
        await pg.wait_for_timeout(600)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(500)
        qoldimi = await pg.query_selector('#ms-qiymat')
        print("  ✓ Escape bilan yopiladi" if not qoldimi else "  ✗ Escape ishlamadi")
        await b.close()
asyncio.run(main())
