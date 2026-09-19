const f=document.getElementById('intake'),work=document.getElementById('work');
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
let RUN=null;
const sev=f=>f.severity==='red'?'risk':'flag-amber';
const card=p=>`<article class="property ${p.verdict.startsWith('Below')||p.verdict.startsWith('High risk')?'dim':''}">
<div class="rank">#${p.rank}</div>
<div>
<h3>${p.name}</h3>
<div class="sub">${money(p.price)} · ${p.units} units · ${p.owner}</div>
<div class="risks">${p.flags.map(x=>`<span class="${sev(x)}" title="${x.text}">${x.flag}</span>`).join('')}</div>
<table class="nums">
<tr><td>Housing cost</td><td>${money(p.housing_cost)}/mo <span class="tag assume">${p.sources.housing_cost}</span></td></tr>
<tr><td>Defensible rent</td><td>${money(p.verified_rent)}/mo <span class="tag src">${p.sources.verified_rent}</span></td></tr>
<tr><td>Coverage</td><td>${p.coverage}%</td></tr>
<tr><td>Residual cash</td><td>${p.weekly_picture} (floor: $${p.floor}/wk)</td></tr>
<tr><td>Permits</td><td>${p.permit} <span class="tag ${p.sources.permit.startsWith('city')?'src':'assume'}">${p.sources.permit}</span></td></tr>
<tr><td>Renovation (output)</td><td>${p.reno_scope} - ${p.reno} <span class="tag assume">${p.sources.reno}</span></td></tr>
</table>
${p.verify.length?`<div class="verify"><b>VERIFY:</b> ${p.verify.join('; ')}</div>`:''}
<details class="stress"><summary>Downside stress panel</summary>${p.stress.map(s=>`<div class="${s.passes?'pass':'fail'}">${s.passes?'✓':'✗'} ${s.test}: residual $${s.residual}/wk</div>`).join('')}</details>
<div class="controls">
<button onclick="decide('${p.id}','approve')">Approve</button>
<button onclick="decide('${p.id}','pass')">Pass</button>
<button onclick="sendback('${p.id}')">Send back</button>
<span id="st-${p.id}" class="st"></span>
</div>
</div>
<div class="metrics">
<div class="metric"><b>${p.coverage}%</b><small>rent coverage</small></div>
<div class="metric"><b>${money(p.residual)}</b><small>cash / week vs $${p.floor} floor</small></div>
<div class="metric"><b>${money(p.verified_rent)}</b><small>defensible rent</small></div>
<div class="metric"><b>${p.evidence}%</b><small>evidence confidence</small></div>
</div>
<div class="verdict ${p.verdict.startsWith('Recommended')?'':'high'}"><b>${p.verdict}</b><span class="sub">score ${p.score} (${Object.entries(p.score_components).map(([k,v])=>k+' '+v).join(', ')} - penalties ${p.penalties})</span></div>
</article>`;
async function decide(pid,dec){
 const r=await fetch('/api/decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:RUN,property_id:pid,decision:dec})});
 const d=await r.json();document.getElementById('st-'+pid).textContent=d.status?`${d.status} (local only)`:d.error;
}
async function sendback(pid){
 const note=prompt('Note for the team on this property:');
 if(!note)return;
 const r=await fetch('/api/sendback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:RUN,property_id:pid,note})});
 const d=await r.json();document.getElementById('st-'+pid).textContent=d.revision?`sent back: "${d.revision.note}" (revision ${d.revision.count})`:d.error;
}
f.onsubmit=async e=>{e.preventDefault();let payload={cash_available_usd:+cash.value,rate_pct:+rate.value,min_living_allowance_usd_per_week:+floor.value,other_monthly_income_usd:0,owner_space:'Studio + fridge + laundry',move_timeline_days:90};
let r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
let d=await r.json();RUN=d.run_id;
agents.innerHTML=d.agents.map(a=>`<span class="agent" title="${a[1]}">${a[0]}</span>`).join('');
summary.textContent=`${d.properties.length} buildings analyzed · price ceiling ${money(d.price_ceiling.max_purchase_price_usd)} [${d.price_ceiling.source}]`;
cards.innerHTML=d.properties.map(card).join('');
work.classList.remove('hide');work.scrollIntoView({behavior:'smooth'})};
