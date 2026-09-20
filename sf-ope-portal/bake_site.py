"""Re-bake the root static Pages snapshot (index.html + site-assets/) from the
real FastAPI app's live output. Run from the sf-ope-portal directory with the
venv active:  python bake_site.py
The static page keeps the 'static snapshot' labeling and never recomputes."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app import app

ROOT = Path(__file__).parent
SITE = ROOT.parent

client = TestClient(app)
demo = client.post('/api/analyze', json={}).json()
rate = demo['financing']['rate_pct']

header = ("/* Static snapshot: analysis baked in from the real FastAPI app's default intake "
          "(see sf-ope-portal/). Form inputs do not recompute on this static page. "
          "Baked with data_mode=%s, financing rate %s%% [%s]. */\n"
          % (demo['data_mode'], rate, demo['financing']['source']))

js = (ROOT / 'static/app.js').read_text()
js = js.replace("""fetch('/api/config').then(r=>r.json()).then(cfg=>{
 rate.value=cfg.rate_pct;rate.dataset.prefilled=String(cfg.rate_pct);
 document.getElementById('rate-note').textContent=cfg.note;
}).catch(()=>{});""",
"""rate.dataset.prefilled=String(DEMO.financing.rate_pct);""")
js = js.replace("""async function decide(pid,dec){
 const r=await fetch('/api/decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:RUN,property_id:pid,decision:dec})});
 const d=await r.json();document.getElementById('st-'+pid).textContent=d.status?`${d.status} (local only)`:d.error;
}
async function sendback(pid){
 const note=prompt('Note for the team on this property:');
 if(!note)return;
 const r=await fetch('/api/sendback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:RUN,property_id:pid,note})});
 const d=await r.json();document.getElementById('st-'+pid).textContent=d.revision?`sent back: "${d.revision.note}" (revision ${d.revision.count})`:d.error;
}""",
"""async function decide(pid,dec){document.getElementById('st-'+pid).textContent='static snapshot - decisions need the live app (see sf-ope-portal/README.md)';}
async function sendback(pid){document.getElementById('st-'+pid).textContent='static snapshot - send-back needs the live app (see sf-ope-portal/README.md)';}""")
js = js.replace("""f.onsubmit=async e=>{e.preventDefault();
 let payload={cash_available_usd:+cash.value,min_living_allowance_usd_per_week:+floor.value,other_monthly_income_usd:0,owner_space:'Studio + fridge + laundry',move_timeline_days:90};
 if(rate.value!==rate.dataset.prefilled)payload.rate_pct=+rate.value;
 let r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 render(await r.json())};""",
"""f.onsubmit=e=>{e.preventDefault();render(DEMO)};""")
assert 'fetch(' not in js.split('DEMO.financing.rate_pct', 1)[1], 'live fetch left in static js'
(SITE / 'site-assets/app.js').write_text(header + 'const DEMO=' + json.dumps(demo) + ';\n' + js)
(SITE / 'site-assets/app.css').write_text((ROOT / 'static/app.css').read_text())

html = """<!doctype html><html><head><meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>SF OPE Homebase</title><link rel="stylesheet" href="site-assets/app.css">
</head>
  <body><main><header><div class="brand">SF OPE <b>Homebase</b></div>
    <div class="pill">Static snapshot - seeded demo</div>
  </header><section class="hero"><div><p class="eyebrow">A HOME THAT RUNS LIKE A SMALL BUSINESS</p><h1>Find the building that gives you room to breathe for your next venture.</h1><p class="lede">Answer a few questions. A silicon team checks rents, layouts, permits, repairs, financing, and downside, then pitches the evidence.</p></div>
    <form id="intake"><label>Cash available <input id="cash" type="number" value="320000"></label><label>Financing rate <div class="suffix"><input id="rate" type="number" step=".01" value="RATEVALUE"><span>%</span></div>
      <small id="rate-note" class="field-note">Baked from the live FRED weekly survey at snapshot time; this static form does not recompute.</small></label>
      <label>Minimum weekly living cash <div class="suffix"><input id="floor" type="number" value="100"><span>/ week</span></div></label>
      <label>Owner space <input value="Studio + fridge + laundry" disabled></label>
      <button>Run property team</button></form></section><section id="work" class="hide"><div class="runbar"><details class="team" id="team"><summary><span class="eyebrow">SILICON TEAM</span> <b>Evidence check complete</b> <span id="dm" class="tag src"></span></summary>
        <ol id="teamlog" class="teamlog"></ol></details><div id="agents" class="agents"></div></div>
        <div class="decision"><div><p class="eyebrow">RANKED PITCHES</p><h2 id="summary"></h2></div><div class="legend"><span class="tag src">SOURCE</span>
          <span class="tag assume">ASSUMPTION</span>
          <span class="risk">RED FLAG</span>
          <span class="flag-amber">AMBER FLAG</span>
        </div></div><div id="cards"></div></section></main>
    <script src="site-assets/app.js"></script>
  </body></html>
""".replace('RATEVALUE', str(rate))
(SITE / 'index.html').write_text(html)
print('baked: data_mode=%s rate=%s props=%d agents=%d' % (demo['data_mode'], rate, len(demo['properties']), len(demo['agents'])))
