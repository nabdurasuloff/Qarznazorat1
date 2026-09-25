# -*- coding: utf-8 -*-
"""Har bir ekranni ochib, xatolik bor-yo'qligini tekshiradi."""
import asyncio, http.server, socketserver, threading, functools, sys, json
from playwright.async_api import async_playwright

ROOT='/home/claude/qarz_nazorat_web/frontend'
PORT=int(sys.argv[1]) if len(sys.argv)>1 else 8891
CHIQISH=sys.argv[2] if len(sys.argv)>2 else '/tmp/claude-0/ekran_natija.json'

EKRANLAR = ['bosh_sahifa','portfel','mijozlar','tahlil','reja_grafik','talabnoma',
            'davo_ariza','biznes_hamroh','sud','mib','sugurta_undirish','vafot',
            '95413','chora','sozlamalar']

httpd=socketserver.TCPServer(("",PORT), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
threading.Thread(target=httpd.serve_forever, daemon=True).start()

async def main():
    natija = {}
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1500,'height':950})
        xatolar=[]
        pg.on('pageerror', lambda e: xatolar.append('PAGEERROR: '+str(e)[:200]))
        pg.on('console', lambda m: xatolar.append('CONSOLE: '+m.text[:200])
              if m.type=='error' and 'ERR_CONNECTION' not in m.text and 'Failed to load resource' not in m.text else None)
        await pg.goto(f'http://127.0.0.1:{PORT}/index.html'); await pg.wait_for_timeout(500)
        await pg.evaluate("API_BASE='http://127.0.0.1:5001/api'")
        await pg.wait_for_timeout(3000)
        xatolar.clear()
        for ekran in EKRANLAR:
            xatolar.clear()
            try:
                await pg.click(f".sb-item[data-key='{ekran}']")
                await pg.wait_for_timeout(2600)
                matn = await pg.inner_text('#main-content')
                sarlavha = await pg.evaluate("document.querySelector('.page-title')?.textContent || ''")
                yuklanmoqda = 'Yuklanmoqda' in matn and len(matn) < 200
                natija[ekran] = {
                    'sarlavha': sarlavha, 'uzunlik': len(matn),
                    'xato_matn': 'Xato:' in matn[:300],
                    'yuklanmoqda_qoldi': yuklanmoqda,
                    'xatolar': list(xatolar),
                }
            except Exception as e:
                natija[ekran] = {'ochilmadi': str(e)[:200], 'xatolar': list(xatolar)}
        await b.close()
    json.dump(natija, open(CHIQISH,'w'), ensure_ascii=False, indent=1)
    yomon=[]
    for e,v in natija.items():
        if v.get('ochilmadi') or v.get('xato_matn') or v.get('yuklanmoqda_qoldi') or v.get('xatolar'):
            yomon.append(e)
        holat = '✓' if e not in yomon else '✗'
        print(f"  {holat} {e:<20} {v.get('sarlavha','')[:38]:<38} {v.get('uzunlik','?')}")
        for x in v.get('xatolar',[])[:2]: print(f"       {x}")
    print(f"\n{len(natija)-len(yomon)}/{len(natija)} ekran muammosiz")
    if yomon: print("MUAMMOLI:", ', '.join(yomon))

asyncio.run(main())
