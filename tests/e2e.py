# End-to-end test. Serve the PARENT folder so the app runs from a subpath (like GitHub Pages):
#   cd .. && python3 -m http.server 8765 --bind 127.0.0.1
#   python3 sleepy-thumb/tests/e2e.py
import json, datetime, os, sys
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8765/sleepy-thumb/'   # served from a subpath, like GitHub Pages
SS=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'screenshots') + os.sep
errors=[]; results=[]
def check(name, cond, info=''):
    results.append((name, bool(cond), info)); print(('PASS ' if cond else 'FAIL ')+name+(' -> '+str(info) if info else ''))
tz=datetime.timezone(datetime.timedelta(hours=7))
start=datetime.datetime(2026,10,17,23,0,tzinfo=tz)
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, is_mobile=True, has_touch=True, timezone_id='Asia/Bangkok', locale='en-US', accept_downloads=True)
    pg=ctx.new_page()
    pg.on('console', lambda m: m.type in ('error','warning') and errors.append(f'{m.type}: {m.text}'))
    pg.on('pageerror', lambda e: errors.append('pageerror: '+str(e)))
    pg.on('requestfailed', lambda r: errors.append('requestfailed: '+r.url))
    ext=[]; pg.on('request', lambda r: (not r.url.startswith('http://127.0.0.1:8765')) and not r.url.startswith('blob:') and not r.url.startswith('data:') and ext.append(r.url))
    pg.clock.install(time=start)
    pg.goto(URL); pg.wait_for_load_state('networkidle')
    t=lambda sel: pg.locator(sel).inner_text().strip()
    check('initial state awake/Ready', 'awake' in pg.evaluate('document.body.className') and t('#timer')=='Ready', t('#timer'))
    # tap target sizes
    sizes=pg.evaluate("""['btnSleep','btnWake','btnDiaper','btnUndo'].map(id=>{const r=document.getElementById(id).getBoundingClientRect();return [id,Math.round(r.width),Math.round(r.height),Math.round(r.top)]})""")
    check('big buttons >= 96px tall', all(s[2]>=96 for s in sizes[:3]), sizes)
    check('buttons fill lower screen (top of pad < 50% of 844)', sizes[0][3] < 422 and sizes[2][3]+sizes[2][2] <= 844, sizes)
    check('undo >=44px', sizes[3][2]>=44, sizes[3])
    pg.tap('#btnWake'); check('Awake before any sleep ignored', pg.evaluate("JSON.parse(localStorage.getItem('sleepyThumb.v1')||'{\"events\":[]}').events.length")==0)
    pg.tap('#btnSleep'); pg.tap('#btnSleep')
    n=pg.evaluate("JSON.parse(localStorage.getItem('sleepyThumb.v1')).events.length")
    check('double Asleep logs once', n==1, n)
    pg.clock.fast_forward('01:30:00')   # -> 00:30 Oct 18
    pg.wait_for_timeout(50)
    check('asleep timer 1h 30m', t('#timer')=='asleep for 1h 30m', t('#timer'))
    check('sleep today counts only after midnight (30m)', t('#sleepToday')=='30m', t('#sleepToday'))
    check('body asleep, Awake emphasized', pg.evaluate("document.body.classList.contains('asleep')") and pg.evaluate("document.getElementById('btnWake').getBoundingClientRect().height > 1.5*document.getElementById('btnSleep').getBoundingClientRect().height"))
    check('Awake aria-label has duration', '1 hour 30 minutes' in (pg.get_attribute('#btnWake','aria-label') or ''), pg.get_attribute('#btnWake','aria-label'))
    pg.wait_for_timeout(3000); pg.evaluate('scrollTo(0,0)'); pg.screenshot(path=SS+'01-asleep.png', animations='disabled')
    pg.tap('#btnWake')
    check('awake state after wake', t('#stateLabel')=='Baby is awake' and t('#timer')=='awake for 0m', t('#timer'))
    pg.clock.fast_forward('01:00:00'); pg.tap('#btnSleep')     # 01:30
    pg.clock.fast_forward('00:45:00'); pg.tap('#btnWake')      # 02:15
    check('total sleep 30m + 45m = 1h 15m', t('#sleepToday')=='1h 15m', t('#sleepToday'))
    pg.clock.fast_forward('00:05:00')
    pg.tap('#btnDiaper'); check('diaper picker opens', pg.is_visible('#diaperPick'))
    pg.tap('#diaperPick .choice[data-kind="dirty"]'); check('picker closes after choice', not pg.is_visible('#diaperPick'))
    pg.clock.fast_forward('00:10:00')
    pg.tap('#btnDiaper'); pg.clock.fast_forward(6000); pg.wait_for_timeout(50)
    check('picker auto-closes after 5s', not pg.is_visible('#diaperPick'))
    kinds=pg.evaluate("JSON.parse(localStorage.getItem('sleepyThumb.v1')).events.filter(e=>e.type==='diaper').map(e=>e.kind)")
    check('diaper kinds dirty then default wet', kinds==['dirty','wet'], kinds)
    pg.clock.fast_forward('00:01:00')
    pg.tap('#btnDiaper'); pg.keyboard.press('Escape')   # mis-tap
    check('3 diapers before undo', t('#diapersToday')=='3', t('#diapersToday'))
    pg.tap('#btnUndo'); check('undo confirm dialog open', pg.is_visible('#dlgConfirm'), t('#confirmMsg'))
    pg.tap('#confirmNo'); check('cancel keeps entry', t('#diapersToday')=='3')
    pg.tap('#btnUndo'); pg.tap('#confirmYes')
    check('undo removes last -> 2 diapers', t('#diapersToday')=='2', t('#diapersToday'))
    pg.reload(); pg.wait_for_load_state('networkidle')
    check('persisted after reload: sleep 1h 15m, 2 diapers', t('#sleepToday')=='1h 15m' and t('#diapersToday')=='2', (t('#sleepToday'), t('#diapersToday')))
    rows=pg.locator('#logList li .what').all_inner_texts()
    times=pg.locator('#logList li .t').all_inner_texts()
    check('log today newest-first (yesterday 11pm sleep excluded)', [r.split('\n')[0] for r in rows]==['Diaper (wet)','Diaper (dirty)','Awake','Asleep','Awake'], list(zip(times,rows)))
    check('wake rows show slept duration', 'slept 45m' in rows[2] and 'slept 1h 30m' in rows[4], rows)
    # edit: change dirty -> both via Edit button
    pg.locator('#logList li').nth(1).locator('button').tap()
    check('edit dialog open', pg.is_visible('#dlgEdit'))
    pg.select_option('#editKind','both'); pg.tap('#editSave')
    check('edit saved', 'Diaper (both)' in pg.locator('#logList li').nth(1).inner_text())
    # edit time of the 01:30 sleep to 01:00 -> total +30m = 1h 45m
    pg.locator('#logList li').nth(3).locator('button').tap()
    pg.fill('#editTime','2026-10-18T01:00'); pg.tap('#editSave')
    check('edit time updates totals (1h 45m)', t('#sleepToday')=='1h 45m', t('#sleepToday'))
    # delete via edit
    pg.locator('#logList li').nth(0).locator('button').tap(); pg.tap('#editDelete'); pg.tap('#confirmYes')
    check('delete via edit -> 1 diaper', t('#diapersToday')=='1', t('#diapersToday'))
    # export
    with pg.expect_download() as d: pg.tap('#btnExportJson')
    data=json.load(open(d.value.path())); check('JSON export has 5 events', len(data['events'])==5, len(data['events']))
    with pg.expect_download() as d: pg.tap('#btnExportCsv')
    csv=open(d.value.path()).read().strip().splitlines(); check('CSV export header + 5 rows', len(csv)==6, csv[0])
    # import round trip
    pg.evaluate("localStorage.clear()"); pg.reload()
    check('cleared storage -> empty', t('#diapersToday')=='0')
    pg.set_input_files('#importFile', files=[{'name':'b.json','mimeType':'application/json','buffer':json.dumps(data).encode()}])
    pg.tap('#confirmYes'); check('import restores data', t('#sleepToday')=='1h 45m' and t('#diapersToday')=='1', (t('#sleepToday'),t('#diapersToday')))
    # midnight rollover: asleep at 23:30 on the 18th, look at 00:20 on the 19th
    pg.clock.set_system_time(datetime.datetime(2026,10,18,23,30,tzinfo=tz)); pg.reload()
    pg.tap('#btnSleep'); pg.clock.fast_forward('00:50:00'); pg.wait_for_timeout(50)
    check('after midnight: today counts 20m of ongoing sleep', t('#sleepToday')=='20m' and t('#timer')=='asleep for 50m', (t('#sleepToday'),t('#timer')))
    check('new day log is empty, diapers reset', t('#diapersToday')=='0' and pg.is_visible('#logEmpty'))
    # screenshot with a log: go back to a day with data
    pg.evaluate("localStorage.clear()"); 
    pg.clock.set_system_time(datetime.datetime(2026,10,18,9,40,tzinfo=tz)); pg.reload()
    pg.set_input_files('#importFile', files=[{'name':'b.json','mimeType':'application/json','buffer':json.dumps(data).encode()}]); pg.tap('#confirmYes')
    pg.tap('#btnDiaper'); pg.tap('#diaperPick .choice[data-kind="wet"]')
    pg.clock.fast_forward('00:20:00'); pg.tap('#btnSleep'); pg.clock.fast_forward('00:25:00'); pg.wait_for_timeout(50)
    pg.wait_for_timeout(3000)
    pg.screenshot(path=SS+'02-log.png', full_page=True)
    # SW + offline
    reg=pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>r?r.scope:null)")
    check('service worker registered at subpath scope', reg=='http://127.0.0.1:8765/sleepy-thumb/', reg)
    # manifest
    m=pg.evaluate("fetch('manifest.json').then(r=>r.json())"); check('manifest loads', m['start_url']=='./')
    b.close()
    # offline test in a fresh context (real clock)
    b=p.chromium.launch(); c2=b.new_context(viewport={'width':390,'height':844}); p2=c2.new_page()
    p2.on('pageerror', lambda e: errors.append('pageerror2: '+str(e)))
    p2.goto(URL); p2.evaluate("navigator.serviceWorker.ready.then(()=>true)"); p2.reload(); p2.wait_for_timeout(500)
    c2.set_offline(True); p2.reload(); check('works offline after first load', p2.locator('#btnSleep').is_visible())
    p2.click('#btnSleep'); check('logging works offline', p2.inner_text('#stateLabel')=='Baby is asleep')
    b.close()
    # reduced motion
    b=p.chromium.launch(); c3=b.new_context(viewport={'width':390,'height':844}, reduced_motion='reduce'); p3=c3.new_page(); p3.goto(URL)
    tr=p3.evaluate("getComputedStyle(document.getElementById('btnSleep')).transitionDuration")
    check('reduced motion disables transitions', all(float(x.strip()[:-1])==0 for x in tr.split(',')), tr)
    b.close()
check('no external requests', not ext, ext)
check('no console errors/warnings', not errors, errors)
print('\n%d/%d passed' % (sum(r[1] for r in results), len(results)))
sys.exit(0 if all(r[1] for r in results) else 1)
