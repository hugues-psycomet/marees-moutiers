#!/usr/bin/env python3
"""Contrôle qualité de l'appli (Playwright, Chromium) — à lancer avant chaque publication.
Vérifie, pour plusieurs largeurs d'écran, thèmes, activités et heures simulées :
  0 erreur JS · 0 débordement horizontal · 0 caractère « tofu » Android (U+202F/U+2009)
  unités insécables (.nb) jamais coupées · saint et date d'en-tête sur une ligne · curseur aligné sur la courbe.
Usage : python3 tools/validate.py [--shots DOSSIER]"""
import asyncio, sys, subprocess, time, pathlib, json
from playwright.async_api import async_playwright
root = pathlib.Path(__file__).resolve().parent.parent
shots = sys.argv[sys.argv.index('--shots')+1] if '--shots' in sys.argv else None
if shots: pathlib.Path(shots).mkdir(parents=True, exist_ok=True)
html = (root/'index.html').read_text(encoding='utf-8')
bad = [c for c in (' ',' ') if c in html]
PORT = 8766
srv = subprocess.Popen([sys.executable,'-m','http.server',str(PORT),'--directory',str(root)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
# heures simulées (Paris) : maintenant réel + un matin + une soirée tardive
OFFSETS = {'now':0, 'morning':None, 'night':None}
async def run():
    fails = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for when in ['now','morning','night']:
          for theme in ['light','dark']:
            for act in ['baignade','voile']:
              for w in [320,360,390,430]:
                if theme=='dark' and w not in (390,): continue
                if when!='now' and w not in (360,): continue
                ctx = await b.new_context(viewport={'width':w,'height':800}, device_scale_factor=2, timezone_id='Europe/Paris', locale='fr-FR', is_mobile=True, has_touch=True)
                init = f"try{{localStorage.setItem('moutiers-theme','{theme}');localStorage.setItem('moutiers-act','{act}')}}catch(e){{}}"
                if when!='now':
                    hh = 7 if when=='morning' else 23
                    init += f""";(function(){{const R=Date.now; const d=new Date(R()); const p=new Intl.DateTimeFormat('en-GB',{{timeZone:'Europe/Paris',hour:'2-digit',hourCycle:'h23'}}).format(d);
                      const off=(({hh}-(+p)+24)%24)*3600e3; Date.now=()=>R()+off; }})();"""
                await ctx.add_init_script(init)
                async def route(r):
                    u=r.request.url
                    if 'posthog' in u or 'cloudflareinsights' in u: return await r.abort()
                    if '/hit' in u: return await r.fulfill(status=200, content_type='application/json', body='{"total":4745,"today":37}')
                    return await r.continue_()
                await ctx.route('**/*', route)
                pg = await ctx.new_page(); errs=[]
                pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.goto(f'http://localhost:{PORT}/index.html'); await pg.wait_for_timeout(2500)
                tag=f'{when}/{theme}/{act}/{w}'
                r = await pg.evaluate("""()=>{
                  const ov = document.documentElement.scrollWidth - innerWidth;
                  const lines = el => { if(!el||!el.getClientRects) return 0; const lh=parseFloat(getComputedStyle(el).lineHeight)||16; return Math.round(el.getBoundingClientRect().height/lh); };
                  const nbBroken = [...document.querySelectorAll('#view-main .nb')].filter(e=>new Set([...e.getClientRects()].filter(r=>r.width>0).map(r=>Math.round(r.bottom))).size>1).map(e=>e.textContent);
                  const rg=document.getElementById('scrubHour');
                  return {ov, nbBroken, saint:lines(document.getElementById('saintLine')), date:lines(document.getElementById('clkDate')),
                          rgMax:+rg.max, rgVal:+rg.value, hero:document.getElementById('departBody').innerText.slice(0,80)} }""")
                # tirer le curseur au milieu et vérifier que le point corail de la courbe suit
                await pg.evaluate("()=>{ const rg=document.getElementById('scrubHour'); rg.value=Math.round(rg.max/2); rg.dispatchEvent(new Event('input',{bubbles:true})); }")
                frac = await pg.evaluate("()=>{ const d=document.getElementById('scrubDot'), svg=document.getElementById('chart'); return (+d.getAttribute('cx')-26)/(360-26-8); }")
                if errs: fails.append((tag,'js',errs))
                if r['ov']>0: fails.append((tag,'overflow',r['ov']))
                if r['nbBroken']: fails.append((tag,'nb',r['nbBroken']))
                if r['saint']>1 or r['date']>1: fails.append((tag,'header-lines',r['saint'],r['date']))
                if abs(frac-0.5)>0.02: fails.append((tag,'slider-misaligned',round(frac,3)))
                if shots and w in (360,390):
                    await pg.evaluate("()=>window.scrollTo(0,0)")
                    await pg.screenshot(path=f"{shots}/{when}-{theme}-{act}-{w}.png", full_page=True)
                print(('OK  ' if not any(f[0]==tag for f in fails) else 'FAIL')+' '+tag+' · '+r['hero'].replace('\n',' | ')[:70])
                await ctx.close()
        await b.close()
    return fails
fails = asyncio.run(run()); srv.terminate()
if bad: fails.append(('file','tofu-chars',bad))
print('\n'+('✅ tout est vert' if not fails else '❌ '+json.dumps(fails, ensure_ascii=False, indent=1)))
sys.exit(1 if fails else 0)
