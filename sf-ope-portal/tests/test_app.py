from fastapi.testclient import TestClient
from app import app
import json
c=TestClient(app)

def run(payload=None):
    return c.post('/api/analyze',json=payload or {}).json()

def test_unwarranted_unit_caught():
    d=run(); ps=d['properties']
    rich=next(p for p in ps if p['id']=='richmond-3')
    exc=next(p for p in ps if p['id']=='excelsior-2')
    assert rich['verified_rent']==6400 and rich['coverage']==68
    assert exc['rank']==1 and exc['rank']<rich['rank']
    assert not rich['verdict'].startswith('Recommended')
    flags=[f['flag'] for f in rich['flags']]
    assert 'Illegal/unwarranted unit' in flags
    assert any(f['severity']=='red' for f in rich['flags'])

def test_coverage_math_exact():
    d=run(); exc=next(p for p in d['properties'] if p['id']=='excelsior-2')
    assert exc['price']==1195000 and exc['housing_cost']==7089 and exc['verified_rent']==7600
    assert exc['coverage']==round(7600/7089*100)==107
    assert exc['residual']==round((7600-7089)/4.33)==118

def test_austerity_flag_and_language():
    d=run({'min_living_allowance_usd_per_week':200})
    for p in d['properties']:
        if p['residual']<200:
            assert p['below_floor'] and p['verdict']=='Below your floor - high risk'
            assert any(f['flag']=='Below living floor' and f['severity']=='red' for f in p['flags'])
    blob=json.dumps(d).lower()
    assert 'does not meet the' in blob and 'floor you set' in blob
    assert 'you could make this work' not in blob

def test_evidence_discipline():
    d=run()
    for p in d['properties']:
        for k in ('price','rent_claim','verified_rent','permit','reno','housing_cost'):
            assert k in p['sources'] and p['sources'][k], (p['id'],k)
    mission=next(p for p in d['properties'] if p['id']=='mission-3')
    assert mission['verify'] and any(f['flag']=='Evidence gap' for f in mission['flags'])

def test_rerank_deterministic():
    a=[(p['id'],p['rank'],p['score'],p['verdict']) for p in run()['properties']]
    b=[(p['id'],p['rank'],p['score'],p['verdict']) for p in run()['properties']]
    assert a==b

def test_ten_roles_and_stress_panel():
    d=run()
    assert len(d['agents'])==10
    for p in d['properties']:
        assert len(p['stress'])==3 and all('passes' in s for s in p['stress'])

def test_decide_and_sendback():
    d=run(); rid=d['run_id']
    r=c.post('/api/decide',json={'run_id':rid,'property_id':'excelsior-2','decision':'approve'}).json()
    assert r['status']=='approve' and 'local status only' in r['effect']
    s=c.post('/api/sendback',json={'run_id':rid,'property_id':'richmond-3','note':'check the in-law again'}).json()
    assert s['revision']['note']=='check the in-law again' and s['property']['id']=='richmond-3'
