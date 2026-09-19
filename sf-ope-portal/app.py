from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import uuid

ROOT=Path(__file__).parent
app=FastAPI(title='SF OPE Homebase')
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

class Intake(BaseModel):
    cash_available_usd:int=320000
    max_purchase_price_usd:Optional[int]=None
    rate_pct:float=6.75
    min_living_allowance_usd_per_week:int=100
    other_monthly_income_usd:int=0
    owner_space:str='Studio + fridge + laundry'
    move_timeline_days:int=90

SEEDED=[
 {'id':'richmond-3','name':'Richmond 3-unit','price':1495000,'units':3,'rent_claim':9900,'verified_rent':6400,'housing_cost':9410,'owner':'Garden studio · kitchenette · shared laundry','owner_fit':0.5,'reno':'Major permit work','reno_scope':'major','permit':'Unit 3 has no permit history','evidence':72,'risk':['UNWARRANTED UNIT','UNSUPPORTED RENT'],'sources':{'price':'listing','rent_claim':'listing','verified_rent':'city-record DBI-2026-0417','permit':'city-record DBI-2026-0417','reno':'assumption','housing_cost':'assumption'},'verify':[]},
 {'id':'excelsior-2','name':'Excelsior legal duplex','price':1195000,'units':2,'rent_claim':7600,'verified_rent':7600,'housing_cost':7089,'owner':'Legal studio · fridge · laundry confirmed','owner_fit':1.0,'reno':'Cosmetic · $18K range','reno_scope':'cosmetic','permit':'Two legal units in seeded city record','evidence':91,'risk':['TIGHT WEEKLY CASH'],'sources':{'price':'listing','rent_claim':'listing','verified_rent':'market-comp 246 Lisbon St $3,800','permit':'city-record DBI-2026-0288','reno':'assumption','housing_cost':'assumption'},'verify':[]},
 {'id':'mission-3','name':'Mission 3-unit','price':1675000,'units':3,'rent_claim':9700,'verified_rent':8950,'housing_cost':10840,'owner':'1BR · kitchen · laundry nearby','owner_fit':0.5,'reno':'Moderate · $55K-$90K','reno_scope':'moderate','permit':'Rear addition requires verification','evidence':78,'risk':['PERMIT VERIFY','PRICE CEILING'],'sources':{'price':'listing','rent_claim':'listing','verified_rent':'market-comp 3025 24th St $3,100','permit':'assumption','reno':'assumption','housing_cost':'assumption'},'verify':['Rear addition has no permit record - is the third unit legal?']},
 {'id':'sunset-2','name':'Outer Sunset duplex','price':1280000,'units':2,'rent_claim':7200,'verified_rent':7000,'housing_cost':8460,'owner':'Studio conversion assumed · laundry','owner_fit':0.5,'reno':'Moderate · $35K-$60K','reno_scope':'moderate','permit':'Conversion feasibility unverified','evidence':75,'risk':['LAYOUT ASSUMPTION'],'sources':{'price':'listing','rent_claim':'listing','verified_rent':'market-comp 2211 Irving St $3,500','permit':'assumption','reno':'assumption','housing_cost':'assumption'},'verify':['Studio conversion legality unverified - confirm the owner unit is legal']}
]

DECISIONS={}
SENDBACKS={}

def weekly_picture(residual):
    if residual<0: return 'rents fall $%d/week short of the housing cost' % abs(residual)
    if residual<50: return '$%d/week - about a week of groceries, nothing else' % residual
    if residual<150: return '$%d/week - groceries and transit, tight' % residual
    return '$%d/week - groceries, transit, phone, with a margin' % residual

def stress(p,intake):
    floor=intake.min_living_allowance_usd_per_week
    other=intake.other_monthly_income_usd
    out=[]
    for label,rent,cost in [
        ('1 month vacancy (one unit)',p['verified_rent']-p['verified_rent']/p['units']/12,p['housing_cost']),
        ('rents drop 10%',p['verified_rent']*0.9,p['housing_cost']),
        ('rate +1%',p['verified_rent'],p['housing_cost']*1.07)]:
        r=round((rent+other-cost)/4.33)
        out.append({'test':label,'residual':r,'passes':r>=floor})
    return out

def brief_for(p,intake):
    floor=intake.min_living_allowance_usd_per_week
    other=intake.other_monthly_income_usd
    coverage_ratio=p['verified_rent']/p['housing_cost']
    coverage=round(coverage_ratio*100)
    residual=round((p['verified_rent']+other-p['housing_cost'])/4.33)
    below=residual<floor
    stress_results=stress(p,intake)
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

def analyze(intake:Intake):
    floor=intake.min_living_allowance_usd_per_week
    rows=[]
    for p in SEEDED:
        b=brief_for(p,intake)
        coc=(p['verified_rent']-p['housing_cost'])*12/max(intake.cash_available_usd,1)
        rows.append({**p,**b,'_coc':coc,
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
    return rows

class Decision(BaseModel):
    run_id:str
    property_id:str
    decision:str  # approve | pass

class SendBack(BaseModel):
    run_id:str
    property_id:str
    note:str

@app.get('/',response_class=HTMLResponse)
def home(): return (ROOT/'templates/index.html').read_text()

@app.post('/api/analyze')
def run(intake:Intake):
    ceiling=intake.max_purchase_price_usd or round(intake.cash_available_usd/0.22)
    return {'run_id':str(uuid.uuid4())[:8],'seeded_demo':True,'intake':intake.model_dump(),
        'price_ceiling':{'max_purchase_price_usd':ceiling,'source':'assumption' if not intake.max_purchase_price_usd else 'listing','note':'Derived from cash + conventional 20% down preset' if not intake.max_purchase_price_usd else 'Set in intake'},
        'properties':analyze(intake),
        'agents':[
            ['Router / Orchestrator','typed task packets emitted per property'],
            ['Acquisition Scout','4 seeded listings screened against price, units, filters'],
            ['Rent-Roll Analyst','claimed rents separated from defensible rents'],
            ['Layout & Owner-Unit Analyst','owner-unit necessities checked'],
            ['Permit & Zoning','unwarranted unit surfaced from seeded city record'],
            ['Construction & Repair','repair ranges attached'],
            ['Renovation Feasibility','scope classified per property'],
            ['Financing Analyst','housing cost scenarios calculated'],
            ['OpEx / Tax','reserves included in seeded cost'],
            ['Downside Reviewer','stress tests run; ranking recomputed after evidence check']]}

@app.post('/api/decide')
def decide(d:Decision):
    if d.decision not in ('approve','pass'): return {'error':'decision must be approve or pass'}
    DECISIONS[(d.run_id,d.property_id)]=d.decision
    return {'run_id':d.run_id,'property_id':d.property_id,'status':d.decision,'effect':'local status only - no messages, filings, offers, or purchases'}

@app.post('/api/sendback')
def sendback(s:SendBack):
    rows=analyze(Intake())
    prop=next((p for p in rows if p['id']==s.property_id),None)
    if not prop: return {'error':'unknown property_id'}
    SENDBACKS.setdefault((s.run_id,s.property_id),[]).append(s.note)
    return {'run_id':s.run_id,'property_id':s.property_id,'revision':{'note':s.note,'count':len(SENDBACKS[(s.run_id,s.property_id)]),'action':'team re-ran the property with the OPE note logged'},'property':prop}
