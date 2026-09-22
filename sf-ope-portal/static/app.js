const f=document.getElementById('intake'),work=document.getElementById('work');
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
let RUN=null;
const sev=f=>f.severity==='red'?'risk':'flag-amber';
const liveblock=p=>{
 if(!p.live)return'';
 const d=p.live.dbi,rb=p.live.rent_board,ov=p.live.overrides||[];
 return`<details class="live"><summary>City record (live)</summary>
${p.live.unit_verdict?`<div class="uv">${p.live.unit_verdict}</div>`:''}
${d?`<div>DBI Building Permits: ${d.permit_count} on record, latest #${d.latest_permit} (${d.latest_status==='filed'?'filed':d.latest_status+', filed'} ${d.latest_filed}).${d.unit_addition_permits.length?` Unit-addition permits: ${d.unit_addition_permits.map(a=>'#'+a.permit_number+' '+a.status+' '+a.from_units+'→'+a.to_units).join('; ')}.`:''}</div>`:''}
${p.live.rent_board_note?`<div>${p.live.rent_board_note}</div>`:''}
${ov.length?`<div class="ov">${ov.map(o=>'Live data: '+o).join('<br>')}</div>`:''}
<div class="srcs">Sources: <a href="https://data.sfgov.org/Housing-and-Buildings/Building-Permits/i98e-djp9">DataSF DBI Permits</a> · <a href="https://data.sfgov.org/Housing-and-Buildings/Rent-Board-Housing-Inventory/gdc7-dmcn">Rent Board Inventory</a></div>
</details>`};
const strblock=p=>{
 if(!p.str)return'';
 const s=p.str;
 return`<details class="str"><summary>Short-term vs long-term rental</summary>
<div>${s.summary} <span class="tag ${s.live?'src':'assume'}">${s.source_tag}</span></div>
<div>${s.verdict}</div>
<div><b>SF rules</b> <span class="tag src">${s.rules_source}</span><ul>${s.rules.map(r=>'<li>'+r+'</li>').join('')}</ul></div>
${(s.market_context||[]).map(m=>'<div>'+m.note+' <span class="tag '+(m.source==='assumption'?'assume':'src')+'">'+m.source+'</span></div>').join('')}
${(s.build_later||[]).length?'<div><b>Build later:</b> '+s.build_later.join(' ')+'</div>':''}
</details>`};
const amenblock=p=>{
 if(!p.amenities)return'';
 const a=p.amenities;
 return`<details class="amen"><summary>Neighborhood amenities</summary>
<div>${a.summary} <span class="tag ${a.live?'src':'assume'}">${a.source_tag}</span></div>
<div>${a.shuttles.note} <span class="tag assume">${a.shuttles.source}</span></div>
</details>`};
const card=p=>`<article class="property ${p.verdict.startsWith('Below')||p.verdict.startsWith('High risk')||p.verdict.startsWith('Outside')?'dim':''}">
<div class="rank">#${p.rank}</div>
<div>
<h3>${p.name}</h3>
<div class="sub">${money(p.price)} · ${p.units} units · ${p.address?`<a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.address.display+', San Francisco, CA')}" target="_blank" rel="noopener">${p.address.display}</a> · `:''}${p.owner}</div>
<div class="risks">${p.flags.map(x=>`<span class="${sev(x)}" title="${x.text}">${x.flag}</span>`).join('')}</div>
<table class="nums">
<tr><td>Housing cost</td><td>${money(p.housing_cost)}/mo <span class="tag assume">${p.sources.housing_cost}</span></td></tr>
<tr><td>Defensible rent</td><td>${money(p.verified_rent)}/mo <span class="tag src">${p.sources.verified_rent}</span></td></tr>
<tr><td>Coverage</td><td>${p.coverage}%</td></tr>
<tr><td>Residual cash</td><td>${p.weekly_picture} (floor: $${p.floor}/wk)</td></tr>
<tr><td>Permits</td><td>${p.permit} <span class="tag ${p.sources.permit.startsWith('city')?'src':'assume'}">${p.sources.permit}</span></td></tr>
<tr><td>Renovation (output)</td><td>${p.reno_scope} - ${p.reno} <span class="tag assume">${p.sources.reno}</span></td></tr>
${p.amenities?`<tr><td>Amenities</td><td>${p.amenities.summary} <span class="tag ${p.amenities.live?'src':'assume'}">${p.amenities.source_tag}</span></td></tr>`:''}
${p.str?`<tr><td>STR vs LTR</td><td>${p.str.summary} <span class="tag ${p.str.live?'src':'assume'}">${p.str.source_tag}</span></td></tr>`:''}
${p.financing_fit?`<tr><td>Financing fit</td><td>${p.financing_fit.summary} <span class="tag assume">${p.financing_fit.source_tag}</span></td></tr>`:''}
${p.rent_benchmark?`<tr><td>Rent benchmark</td><td>${p.rent_benchmark.summary} <span class="tag ${p.rent_benchmark.live?'src':'assume'}">${p.rent_benchmark.source_tag}</span></td></tr>`:''}
${p.geo_how?`<tr><td>Your area</td><td>${p.geo_match?'Matches: '+p.geo_how:'No match'} </td></tr>`:''}
</table>
${amenblock(p)}${strblock(p)}
${p.verify.length?`<div class="verify"><b>VERIFY:</b> ${p.verify.join('; ')}</div>`:''}
${liveblock(p)}
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
function render(d){
 RUN=d.run_id;
 document.getElementById('dm').textContent=d.data_mode;
 if(d.events){window.LAST_EVENTS=d.events;replay(d.events);}
 teamlog.innerHTML=d.team_log.map(x=>`<li>${x}</li>`).join('');
 agents.innerHTML=d.agents.map(a=>`<details class="agent"><summary>${a.name}</summary><div class="ad"><p><b>This run:</b> ${a.did}</p><p><b>Asks:</b> ${a.question}</p><p><b>Key evidence:</b> ${a.evidence}</p></div></details>`).join('');
 summary.textContent=`${d.geo_area?`area "${d.geo_area}": ${d.geo_matched} of ${d.properties.length} match · `:''}${d.properties.length} buildings analyzed · price ceiling ${money(d.price_ceiling.max_purchase_price_usd)} [${d.price_ceiling.source}] · financing ${d.financing.rate_pct}% [${d.financing.source}]`;
 cards.innerHTML=d.properties.map(card).join('');
 initPropertyReveal();
 work.classList.remove('hide');work.scrollIntoView({behavior:'smooth'});
}
fetch('/api/config').then(r=>r.json()).then(cfg=>{
 rate.value=cfg.rate_pct;rate.dataset.prefilled=String(cfg.rate_pct);
 document.getElementById('rate-note').textContent=cfg.note;
}).catch(()=>{});
f.onsubmit=async e=>{e.preventDefault();
 let ownerSpace=[...document.querySelectorAll('input[name="owner-space"]:checked')].map(x=>x.value).join(' + ');
 let payload={cash_available_usd:+cash.value,min_living_allowance_usd_per_week:+floor.value,other_monthly_income_usd:+income.value,current_rent_usd:+rent.value,credit_score:credit.value?+credit.value:null,owner_space:ownerSpace,move_timeline_days:90};
 if(rate.value!==rate.dataset.prefilled)payload.rate_pct=+rate.value;
 if(geo.value.trim())payload.geo_area=geo.value.trim();
 let r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 render(await r.json())};

let REPLAY=null;
function replay(events){
 if(!events||!events.length)return;
 const feed=document.getElementById('feed');if(!feed)return;
 if(REPLAY)clearInterval(REPLAY);
 feed.innerHTML='';
 const tiles=[...document.querySelectorAll('details.agent')];
 let i=0;
 const step=()=>{
  tiles.forEach(t=>t.classList.remove('on'));
  if(i>=events.length){REPLAY=null;return;}
  const e=events[i++];
  const tile=tiles.find(t=>t.querySelector('summary')&&t.querySelector('summary').textContent.trim().startsWith(e.agent));
  if(tile)tile.classList.add('on');
  const li=document.createElement('li');
  li.className='e-'+e.kind;
  li.innerHTML='<b>'+e.agent+'</b>'+(e.property_id?' <span class="pid">'+e.property_id+'</span>':'')+': '+e.text;
  feed.appendChild(li);
  feed.scrollTop=feed.scrollHeight;
 };
 step();
 REPLAY=setInterval(step,480);
}
document.addEventListener('click',e=>{if(e.target&&e.target.id==='replay'&&window.LAST_EVENTS)replay(LAST_EVENTS);});


function initOwnerSpaceSummary(){
 const root=document.querySelector('.checkdrop');if(!root)return;
 const update=()=>{const picked=[...root.querySelectorAll('input:checked')].map(x=>x.value);root.querySelector('.check-summary').textContent=picked.join(', ')||'Select essentials'};
 root.addEventListener('change',update);update();
}
function initPropertyReveal(){
 const tiles=[...document.querySelectorAll('#cards .property')];
 if(!('IntersectionObserver' in window)){tiles.forEach(t=>t.classList.add('revealed'));return;}
 tiles.forEach(t=>t.classList.add('reveal-ready'));
 const io=new IntersectionObserver((entries)=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('revealed');io.unobserve(entry.target)}}),{threshold:.16,rootMargin:'0px 0px -8% 0px'});
 tiles.forEach((t,i)=>{t.style.transitionDelay=Math.min(i*70,210)+'ms';io.observe(t)});
}
initOwnerSpaceSummary();
