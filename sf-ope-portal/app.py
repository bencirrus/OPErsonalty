from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import uuid

import livedata

ROOT=Path(__file__).parent
app=FastAPI(title='SF OPE Homebase')
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

SEEDED_RATE_PCT=6.75  # offline fallback only; live default comes from FRED MORTGAGE30US

class Intake(BaseModel):
    cash_available_usd:int=320000
    max_purchase_price_usd:Optional[int]=None
    rate_pct:Optional[float]=None  # None = use the live FRED rate (seeded fallback offline)
    min_living_allowance_usd_per_week:int=100
    other_monthly_income_usd:int=0
    owner_space:str='Studio + fridge + laundry'
    move_timeline_days:int=90

# Seeded demo listings (fictional). Addresses are seeded listing data; the
# Permit & Zoning Analyst checks them against live DataSF city records when
# online and falls back to the seeded city record offline.
SEEDED=[
 {'id':'richmond-3','name':'Richmond 3-unit','price':1495000,'units':3,'rent_claim':9900,'verified_rent':6400,'housing_cost':9410,'owner':'Garden studio · kitchenette · shared laundry','owner_fit':0.5,'reno':'Major permit work','reno_scope':'major','permit':'Unit 3 has no permit history','evidence':72,'risk':['UNWARRANTED UNIT','UNSUPPORTED RENT'],'sources':{'price':'listing','rent_claim':'listing','verified_rent':'city-record DBI-2026-0417','permit':'city-record DBI-2026-0417','reno':'assumption','housing_cost':'assumption'},'verify':[],
  'address':{'street_number':'648','street_name':'06th','street_suffix':'Av','display':'648 6th Ave, Inner Richmond'},'block_address':'600 Block of 06TH AVE'},
 {'id':'excelsior-2','name':'Excelsior legal duplex','price':1195000,'units':2,'rent_claim':7600,'verified_rent':7600,'housing_cost':7089,'owner':'Legal studio · fridge · laundry confirmed','owner_fit':1.0,'reno':'Cosmetic · $18K range','reno_scope':'cosmetic','permit':'Two legal units in seeded city record','evidence':91,'risk':['TIGHT WEEKLY CASH'],'sources':{'price':'listing','rent_claim':'listing','verified_rent':'market-comp 246 Lisbon St $3,800','permit':'city-record DBI-2026-0288','reno':'assumption','housing_cost':'assumption'},'verify':[],
  'address':{'street_number':'126','street_name':'Lisbon','street_suffix':'St','display':'126 Lisbon St, Excelsior'},'block_address':'100 Block of LISBON ST'},
 {'id':'mission-3','name':'Mission 3-unit','price':1675000,'units':3,'rent_claim':9700,'verified_rent':8950,'housing_cost':10840,'owner':'1BR · kitchen · laundry nearby','owner_fit':0.5,'reno':'Moderate · $55K-$90K','reno_scope':'moderate','permit':'Rear addition requires verification','evidence':78,'risk':['PERMIT VERIFY','PRICE CEILING'],'sources':{'price':'listing','rent_claim':'listing','verified_rent':'market-comp 3025 24th St $3,100','permit':'assumption','reno':'assumption','housing_cost':'assumption'},'verify':['Rear addition has no permit record - is the third unit legal?'],
  'address':{'street_number':'737','street_name':'Guerrero','street_suffix':'St','display':'737 Guerrero St, Mission'},'block_address':'700 Block of GUERRERO ST'},
 {'id':'sunset-2','name':'Outer Sunset duplex','price':1280000,'units':2,'rent_claim':7200,'verified_rent':7000,'housing_cost':8460,'owner':'Studio conversion assumed · laundry','owner_fit':0.5,'reno':'Moderate · $35K-$60K','reno_scope':'moderate','permit':'Conversion feasibility unverified','evidence':75,'risk':['LAYOUT ASSUMPTION'],'sources':{'price':'listing','rent_claim':'listing','verified_rent':'market-comp 2211 Irving St $3,500','permit':'assumption','reno':'assumption','housing_cost':'assumption'},'verify':['Studio conversion legality unverified - confirm the owner unit is legal'],
  'address':{'street_number':'1414','street_name':'38th','street_suffix':'Av','display':'1414 38th Ave, Outer Sunset'},'block_address':'1400 Block of 38TH AVE'}
]

DECISIONS={}
SENDBACKS={}

def weekly_picture(residual):
    if residual<0: return 'rents fall $%d/week short of the housing cost' % abs(residual)
    if residual<50: return '$%d/week - about a week of groceries, nothing else' % residual
    if residual<150: return '$%d/week - groceries and transit, tight' % residual
    return '$%d/week - groceries, transit, phone, with a margin' % residual

def resolve_rate(intake):
    """(rate_pct, source_label, live). Live FRED first, seeded fallback offline."""
    if intake.rate_pct is not None:
        return intake.rate_pct,'set in intake',False
    live=livedata.fred_rate()
    if live:
        return live[0],'FRED MORTGAGE30US (Freddie Mac PMMS), week ending %s' % live[1],True
    return SEEDED_RATE_PCT,'seeded fallback %s%% (FRED unreachable)' % SEEDED_RATE_PCT,False

def stress(p,intake,rate_pct):
    floor=intake.min_living_allowance_usd_per_week
    other=intake.other_monthly_income_usd
    out=[]
    for label,rent,cost in [
        ('1 month vacancy (one unit)',p['verified_rent']-p['verified_rent']/p['units']/12,p['housing_cost']),
        ('rents drop 10%',p['verified_rent']*0.9,p['housing_cost']),
        ('rate +1%% (%.2f%% → %.2f%%)' % (rate_pct,rate_pct+1),p['verified_rent'],p['housing_cost']*1.07)]:
        r=round((rent+other-cost)/4.33)
        out.append({'test':label,'residual':r,'passes':r>=floor})
    return out

def brief_for(p,intake,rate_pct):
    floor=intake.min_living_allowance_usd_per_week
    other=intake.other_monthly_income_usd
    coverage_ratio=p['verified_rent']/p['housing_cost']
    coverage=round(coverage_ratio*100)
    residual=round((p['verified_rent']+other-p['housing_cost'])/4.33)
    below=residual<floor
    stress_results=stress(p,intake,rate_pct)
    stress_fail=any(not s['passes'] for s in stress_results)
    permit_uncertain=any('VERIFY' in x for x in p['risk']) or 'requires verification' in p['permit'] or 'unverified' in p['permit']
    flags=[]
    if below: flags.append({'severity':'red','flag':'Below living floor','text':'Residual weekly cash $%d does not meet the $%d/week floor you set.' % (residual,floor)})
    if 'UNWARRANTED UNIT' in p['risk']: flags.append({'severity':'red','flag':'Illegal/unwarranted unit','text':'Rent math included a unit with no legal record; rent roll repriced without it.'})
    if permit_uncertain: flags.append({'severity':'amber','flag':'Permit uncertainty','text':p['permit']+'.'})
    if stress_fail: flags.append({'severity':'amber','flag':'Stress failure','text':'A downside test (vacancy, rent cut, or rate shock) drops residual cash below your floor.'})
    if p['reno_scope']=='major': flags.append({'severity':'amber','flag':'Major renovation scope','text':'Scope is major permit work: '+p['reno']+'.'})
    if p['verify']: flags.append({'severity':'amber','flag':'Evidence gap','text':'Open verification item: '+p['verify'][0]})
    red=any(f['severity']=='red' for f in flags)
    if below: verdict='Below your floor - high risk'
    elif red: verdict='High risk - not recommended'
    elif flags: verdict='Recommended with flags'
    else: verdict='Recommended'
    return {'coverage':coverage,'coverage_ratio':round(coverage_ratio,4),'residual':residual,'below_floor':below,
            'weekly_picture':weekly_picture(residual),'floor':floor,'verdict':verdict,'flags':flags,
            'stress':stress_results,'stress_fail':stress_fail,'permit_uncertain':permit_uncertain}

def merge_live(p,live):
    """Overlay live city records on a seeded property. Live wins; overrides are shown."""
    if not live: return None
    dbi=live.get('dbi'); rb=live.get('rent_board')
    block={'dbi':dbi,'rent_board':rb,'overrides':[],'unit_verdict':None}
    seeded_concern = p['permit'] if ('unverified' in p['permit'] or 'requires verification' in p['permit']) else None
    if dbi:
        p['sources']['permit']='city-record DBI #%s (%d permits on record)' % (dbi['latest_permit'],dbi['permit_count'])
        units_record=dbi['max_units_on_record']
        strong_adds=[a for a in dbi['unit_addition_permits'] if a['status'] in ('issued','complete') and a['to_units']>=p['units']]
        base='Live DBI record: %d permits, latest #%s (status %s, filed %s)' % (dbi['permit_count'],dbi['latest_permit'],dbi['latest_status'],dbi['latest_filed'])
        if units_record is not None and units_record < p['units'] and not strong_adds:
            block['unit_verdict']='Live city record shows %d legal unit(s); the listing claims %d.' % (units_record,p['units'])
            p['permit']='%s; record shows %d legal units, listing claims %d.' % (base,units_record,p['units'])
            if 'UNWARRANTED UNIT' not in p['risk']:
                p['risk']=p['risk']+['UNWARRANTED UNIT']
                block['overrides'].append('Seeded record did not flag an unwarranted unit; the live DBI record shows fewer legal units than the listing claims, so the Reviewer flags it.')
            else:
                block['overrides'].append('Live DBI record confirms the seeded catch: fewer legal units on record than the listing claims.')
        elif units_record is not None and units_record < p['units'] and strong_adds:
            a=strong_adds[0]
            block['unit_verdict']='Live city record shows %d legal unit(s); permit #%s (%s) legalizes unit %d - not final yet.' % (units_record,a['permit_number'],a['status'],a['to_units'])
            p['permit']='%s; record shows %d legal units, and permit #%s (%s, filed %s) legalizes unit %d - count not final, still requires verification.' % (base,units_record,a['permit_number'],a['status'],a['filed'],a['to_units'])
            block['overrides'].append('Live DBI record shows the extra unit is mid-legalization (permit #%s, %s), not paperless: kept as an amber verify item, not a red unwarranted flag.' % (a['permit_number'],a['status']))
        elif units_record is not None:
            p['permit']='%s; record supports %d units.' % (base,units_record)
            block['unit_verdict']='Live city record supports %d units on record.' % units_record
            if 'UNWARRANTED UNIT' in p['risk']:
                p['risk']=[r for r in p['risk'] if r!='UNWARRANTED UNIT']
                block['overrides'].append('Live DBI record shows enough legal units for the listing; the seeded unwarranted-unit call is retracted. Live data wins.')
        if seeded_concern and 'unverified' not in p['permit'] and 'requires verification' not in p['permit']:
            p['permit']=p['permit']+' Seeded concern stands: '+seeded_concern+'.'
    if rb:
        if rb['submissions']:
            block['rent_board_note']='Rent Board Housing Inventory: %d submission(s) on %s; latest reports %g unit(s), signed %s.' % (rb['submissions'],rb['block_address'],rb['latest_unit_count'] or 0,rb['latest_signed'])
        else:
            block['rent_board_note']='Rent Board Housing Inventory: no submissions on record for %s.' % (p.get('block_address') or 'this block')
    return block

def analyze(intake:Intake,rate_pct:float):
    floor=intake.min_living_allowance_usd_per_week
    rows=[]
    any_live=False
    for seed in SEEDED:
        p={**seed,'risk':list(seed['risk']),'sources':dict(seed['sources']),'verify':list(seed['verify'])}
        live_block=merge_live(p,livedata.city_record(seed))
        any_live=any_live or bool(live_block and live_block.get('dbi'))
        b=brief_for(p,intake,rate_pct)
        coc=(p['verified_rent']-p['housing_cost'])*12/max(intake.cash_available_usd,1)
        rows.append({**p,**b,'live':live_block,'_coc':coc,
            'score_components':{
                'coverage':round(40*min(b['coverage_ratio'],1.0),2),
                'residual':round(20*max(min(b['residual']/(2*floor),1),0),2) if floor>0 else 0,
                'cash_on_cash':0,  # normalized below
                'owner_unit_fit':round(10*p['owner_fit'],2),
                'evidence_confidence':round(15*p['evidence']/100,2)}})
    cocs=[r['_coc'] for r in rows]
    lo,hi=min(cocs),max(cocs)
    for r in rows:
        r['score_components']['cash_on_cash']=round(15*((r['_coc']-lo)/(hi-lo) if hi>lo else 0.5),2)
        base=sum(r['score_components'].values())
        penalties=(30 if 'UNWARRANTED UNIT' in r['risk'] else 0)+(25 if r['below_floor'] else 0)+(10 if r['permit_uncertain'] else 0)+(10 if r['stress_fail'] else 0)
        r['penalties']=penalties
        r['score']=round(base-penalties,2)
        del r['_coc']
    rows.sort(key=lambda x:x['score'],reverse=True)
    for i,r in enumerate(rows): r['rank']=i+1
    return rows,any_live

class Decision(BaseModel):
    run_id:str
    property_id:str
    decision:str  # approve | pass

class SendBack(BaseModel):
    run_id:str
    property_id:str
    note:str

def agent_roster(live_on,rate_pct,rate_source):
    city_line=('live DataSF DBI permits + Rent Board Housing Inventory checked for all 4 seeded addresses'
               if live_on else 'seeded city record checked (live DataSF unreachable - offline fallback)')
    rate_line='housing cost scenarios calculated at %.2f%% [%s]' % (rate_pct,rate_source)
    return [
      {'name':'Router / Orchestrator','did':'typed task packets emitted per property','question':'Who needs to look at this building, and in what order?','evidence':'run log: all ten roles executed in sequence per property'},
      {'name':'Acquisition Scout','did':'4 seeded listings screened against price, units, filters','question':'Which buildings fit the budget and basic filters at all?','evidence':'listing screens, price ceiling [assumption]'},
      {'name':'Rent-Roll Analyst','did':'claimed rents separated from defensible rents','question':'Which rents are real, and which are wishful?','evidence':'claimed vs defensible rent per unit, market comps [market-comp]'},
      {'name':'Layout & Owner-Unit Analyst','did':'owner-unit necessities checked','question':'Can the owner actually live here?','evidence':'owner-unit checklist: legal space, fridge, laundry'},
      {'name':'Permit & Zoning Analyst','did':city_line,'question':'Is every unit in the listing actually legal?','evidence':'[city-record] SF DBI Building Permits (data.sfgov.org i98e-djp9) + Rent Board Housing Inventory (gdc7-dmcn), keyless live API; seeded record offline'},
      {'name':'Construction & Repair Estimator','did':'repair ranges attached','question':'What will it cost to fix?','evidence':'repair range per building [assumption]'},
      {'name':'Renovation Feasibility Planner','did':'scope classified per property','question':'How big is the renovation lift?','evidence':'scope classes: cosmetic / moderate / major permit work'},
      {'name':'Financing Analyst','did':rate_line,'question':'What does the building cost to hold each month?','evidence':'[city-record] live 30-yr rate from FRED MORTGAGE30US (Freddie Mac PMMS) when online; seeded %s%% offline' % SEEDED_RATE_PCT},
      {'name':'OpEx & Tax Analyst','did':'reserves included in seeded cost','question':'What does it cost to run, not just to buy?','evidence':'reserves + tax inside housing cost [assumption]'},
      {'name':'Downside Reviewer','did':'stress tests run; ranking recomputed after evidence check','question':'What breaks first when something goes wrong?','evidence':'stress panel (vacancy, rent cut, rate shock) at the live rate; penalties applied to the ranking'}]

@app.get('/',response_class=HTMLResponse)
def home(): return (ROOT/'templates/index.html').read_text()

@app.get('/api/config')
def config():
    rate,source,live=resolve_rate(Intake())
    return {'rate_pct':rate,'rate_source':source,'rate_live':live,
            'note':'Rate pre-filled from the live FRED weekly survey when online; edit it to use your own.'}

@app.post('/api/analyze')
def run(intake:Intake):
    rate,rate_source,rate_live=resolve_rate(intake)
    ceiling=intake.max_purchase_price_usd or round(intake.cash_available_usd/0.22)
    properties,any_live=analyze(intake,rate)
    team_log=[
        'Router / Orchestrator split the intake into 4 typed task packets, one per building.',
        'Acquisition Scout screened the seeded listings against the price ceiling.',
        'Rent-Roll, Layout & Owner-Unit, Construction & Repair, Renovation Feasibility, Financing, and OpEx & Tax specialists filed evidence-tagged findings per building.',
        'Permit & Zoning Analyst checked '+('live DataSF DBI permits and Rent Board Housing Inventory for each seeded address' if any_live else 'the seeded city record (live DataSF unreachable - offline fallback)')+'.',
        'Downside Reviewer ran 3 downside stress tests per building at %.2f%% and recomputed the ranking after the evidence check.' % rate,
    ]
    return {'run_id':str(uuid.uuid4())[:8],'team_log':team_log,'seeded_demo':True,'data_mode':'live city records' if any_live else 'seeded (offline)','intake':intake.model_dump(),
        'financing':{'rate_pct':rate,'source':rate_source,'live':rate_live,'series_url':livedata.FRED_SERIES_URL},
        'price_ceiling':{'max_purchase_price_usd':ceiling,'source':'assumption' if not intake.max_purchase_price_usd else 'listing','note':'Derived from cash + conventional 20% down preset' if not intake.max_purchase_price_usd else 'Set in intake'},
        'properties':properties,
        'agents':agent_roster(any_live,rate,rate_source)}

@app.post('/api/decide')
def decide(d:Decision):
    if d.decision not in ('approve','pass'): return {'error':'decision must be approve or pass'}
    DECISIONS[(d.run_id,d.property_id)]=d.decision
    return {'run_id':d.run_id,'property_id':d.property_id,'status':d.decision,'effect':'local status only - no messages, filings, offers, or purchases'}

@app.post('/api/sendback')
def sendback(s:SendBack):
    rows,_=analyze(Intake(),SEEDED_RATE_PCT)
    prop=next((p for p in rows if p['id']==s.property_id),None)
    if not prop: return {'error':'unknown property_id'}
    SENDBACKS.setdefault((s.run_id,s.property_id),[]).append(s.note)
    return {'run_id':s.run_id,'property_id':s.property_id,'revision':{'note':s.note,'count':len(SENDBACKS[(s.run_id,s.property_id)]),'action':'team re-ran the property with the OPE note logged'},'property':prop}
