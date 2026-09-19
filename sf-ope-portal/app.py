from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import json, uuid

ROOT=Path(__file__).parent
app=FastAPI(title='SF OPE Homebase')
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

class Intake(BaseModel):
    cash_available_usd:int=320000
    rate_pct:float=6.75
    min_living_allowance_usd_per_week:int=100
    owner_space:str='Studio + fridge + laundry'
    move_timeline_days:int=90

SEEDED=[
 {'id':'richmond-3','name':'Richmond 3-unit','price':1495000,'units':3,'rent_claim':9900,'verified_rent':6400,'housing_cost':9410,'owner':'Garden studio · kitchenette · shared laundry','reno':'Major permit work','permit':'Unit 3 has no permit history','evidence':72,'risk':['UNWARRANTED UNIT','UNSUPPORTED RENT']},
 {'id':'excelsior-2','name':'Excelsior legal duplex','price':1195000,'units':2,'rent_claim':7600,'verified_rent':7600,'housing_cost':7089,'owner':'Legal studio · fridge · laundry confirmed','reno':'Cosmetic · $18K range','permit':'Two legal units in seeded city record','evidence':91,'risk':['TIGHT WEEKLY CASH']},
 {'id':'mission-3','name':'Mission 3-unit','price':1675000,'units':3,'rent_claim':9700,'verified_rent':8950,'housing_cost':10840,'owner':'1BR · kitchen · laundry nearby','reno':'Moderate · $55K-$90K','permit':'Rear addition requires verification','evidence':78,'risk':['PERMIT VERIFY','PRICE CEILING']},
 {'id':'sunset-2','name':'Outer Sunset duplex','price':1280000,'units':2,'rent_claim':7200,'verified_rent':7000,'housing_cost':8460,'owner':'Studio conversion assumed · laundry','reno':'Moderate · $35K-$60K','permit':'Conversion feasibility unverified','evidence':75,'risk':['LAYOUT ASSUMPTION']}
]

def analyze(intake:Intake):
 rows=[]
 for p in SEEDED:
  coverage=round(p['verified_rent']/p['housing_cost']*100)
  residual=round((p['verified_rent']-p['housing_cost'])/4.33)
  below=residual<intake.min_living_allowance_usd_per_week
  score=round(.4*min(coverage,110)+.2*max(min(residual/2,100),0)+.15*8+.1*(100 if 'confirmed' in p['owner'] else 60)+.15*p['evidence'])
  penalties=(30 if 'UNWARRANTED UNIT' in p['risk'] else 0)+(25 if below else 0)+(10 if any('VERIFY' in x or 'ASSUMPTION' in x for x in p['risk']) else 0)
  rows.append({**p,'coverage':coverage,'residual':residual,'below_floor':below,'score':score-penalties,'rank_reason':'Recommended' if not below and not any(x in p['risk'] for x in ['UNWARRANTED UNIT','PRICE CEILING']) else 'High risk · not recommended'})
 rows.sort(key=lambda x:x['score'],reverse=True)
 for i,r in enumerate(rows):r['rank']=i+1
 return rows

@app.get('/',response_class=HTMLResponse)
def home():return (ROOT/'templates/index.html').read_text()
@app.post('/api/analyze')
def run(intake:Intake):
 return {'run_id':str(uuid.uuid4())[:8],'seeded_demo':True,'intake':intake.model_dump(),'properties':analyze(intake),'agents':[
  ['Acquisition Scout','4 seeded listings screened'],['Rent-Roll Analyst','claimed rents separated from defensible rents'],['Layout Analyst','owner-unit necessities checked'],['Permit & Zoning','unwarranted unit surfaced'],['Construction','repair ranges attached'],['Financing','housing cost scenarios calculated'],['OpEx / Tax','reserves included in seeded cost'],['Downside Reviewer','ranking recomputed after evidence check']
 ]}
