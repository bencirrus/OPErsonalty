from fastapi.testclient import TestClient
from app import app, SEEDED
import livedata
import json
c=TestClient(app)

def run(payload=None):
    return c.post('/api/analyze',json=payload or {}).json()

def _dbi(units,latest='209900001',status='filed',filed='2026-09-18',count=4,adds=()):
    return {'permit_count':count,'latest_permit':latest,'latest_status':status,'latest_filed':filed,
            'latest_units_existing':float(units),'max_units_on_record':float(units),
            'max_units_proposed':max([units]+[a['to_units'] for a in adds]) if adds else float(units),
            'unit_addition_permits':list(adds),'dataset_url':'https://data.sfgov.org/x'}

def _add(number,status,to_units,from_units=2.0):
    return {'permit_number':number,'status':status,'filed':'2026-09-18',
            'from_units':from_units,'to_units':float(to_units),'description':'legalize unit'}

def _rb(n=0):
    return {'submissions':n,'block_address':'600 Block of 06TH AVE' if n else None,
            'latest_unit_count':1.0 if n else None,'latest_signed':'2026-08-25' if n else None,
            'dataset_url':'https://data.sfgov.org/y'}

def _live(per_id):
    m={'richmond-3':{'dbi':_dbi(2),'rent_board':_rb(1)},
       'excelsior-2':{'dbi':_dbi(2,latest='209900002',count=5),'rent_board':_rb(0)},
       'mission-3':{'dbi':_dbi(2,latest='209900003',count=11,adds=[_add('209900003','issued',3)]),'rent_board':_rb(0)},
       'sunset-2':{'dbi':_dbi(2,latest='209900004',count=7),'rent_board':_rb(0)}}
    return m.get(per_id)

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

EXPECTED_TITLES=['Router / Orchestrator','Acquisition Scout','Rent-Roll Analyst','Layout & Owner-Unit Analyst','Neighborhood & Amenities Analyst','Permit & Zoning Analyst','Construction & Repair Estimator','Renovation Feasibility Planner','Financing Analyst','OpEx & Tax Analyst','Short-Term Rental Analyst','Downside Reviewer']

def test_ten_roles_and_stress_panel():
    d=run()
    assert len(d['agents'])==12
    assert [a['name'] for a in d['agents']]==EXPECTED_TITLES
    for a in d['agents']:
        assert a['did'] and a['question'] and a['evidence'], a['name']
    assert len(d['team_log'])>=5
    for p in d['properties']:
        assert len(p['stress'])==3 and all('passes' in s for s in p['stress'])

def test_decide_and_sendback():
    d=run(); rid=d['run_id']
    r=c.post('/api/decide',json={'run_id':rid,'property_id':'excelsior-2','decision':'approve'}).json()
    assert r['status']=='approve' and 'local status only' in r['effect']
    s=c.post('/api/sendback',json={'run_id':rid,'property_id':'richmond-3','note':'check the in-law again'}).json()
    assert s['revision']['note']=='check the in-law again' and s['property']['id']=='richmond-3'

def test_offline_fallback_seeded_rate_and_records():
    d=run()
    assert d['data_mode']=='seeded (offline)'
    assert d['financing']['rate_pct']==6.75 and d['financing']['live'] is False
    for p in d['properties']:
        assert p['live'] is None

def test_live_city_records_merge(monkeypatch):
    monkeypatch.setattr(livedata,'city_record',lambda prop: _live(prop['id']))
    monkeypatch.setattr(livedata,'fred_rate',lambda: (6.95,'2026-09-17'))
    d=run()
    assert d['data_mode']=='live city records'
    assert d['financing']['rate_pct']==6.95 and d['financing']['live'] is True
    assert 'FRED MORTGAGE30US' in d['financing']['source'] and '2026-09-17' in d['financing']['source']
    rich=next(p for p in d['properties'] if p['id']=='richmond-3')
    assert rich['sources']['permit'].startswith('city-record DBI #209900001')
    assert 'UNWARRANTED UNIT' in rich['risk']
    assert rich['live']['unit_verdict']=='Live city record shows 2 legal unit(s); the listing claims 3.'
    assert rich['live']['rent_board_note'].startswith('Rent Board Housing Inventory: 1 submission(s)')
    exc=next(p for p in d['properties'] if p['id']=='excelsior-2')
    assert 'UNWARRANTED UNIT' not in exc['risk']
    assert 'supports 2 units' in exc['live']['unit_verdict']
    assert any('6.95' in s['test'] for s in exc['stress'])

def test_live_wins_retracts_seeded_unwarranted(monkeypatch):
    def cr(prop):
        if prop['id']=='richmond-3': return {'dbi':_dbi(3),'rent_board':_rb(0)}
        return None
    monkeypatch.setattr(livedata,'city_record',cr)
    d=run()
    rich=next(p for p in d['properties'] if p['id']=='richmond-3')
    assert 'UNWARRANTED UNIT' not in rich['risk']
    assert not any(f['flag']=='Illegal/unwarranted unit' for f in rich['flags'])
    assert any('retracted' in o for o in rich['live']['overrides'])

def test_live_legalization_in_flight_is_amber_not_red(monkeypatch):
    monkeypatch.setattr(livedata,'city_record',lambda prop: _live(prop['id']))
    d=run()
    mission=next(p for p in d['properties'] if p['id']=='mission-3')
    assert 'UNWARRANTED UNIT' not in mission['risk']
    assert 'not final' in mission['live']['unit_verdict']
    assert mission['permit_uncertain'] is True
    assert any(f['flag']=='Permit uncertainty' for f in mission['flags'])
    assert not any(f['severity']=='red' and f['flag']=='Illegal/unwarranted unit' for f in mission['flags'])

def test_rate_override_in_intake_beats_live(monkeypatch):
    monkeypatch.setattr(livedata,'fred_rate',lambda: (6.95,'2026-09-17'))
    d=run({'rate_pct':5.5})
    assert d['financing']['rate_pct']==5.5 and d['financing']['live'] is False


def test_geo_filter_zip():
    d=run({'geo_area':'94118'})
    assert d['geo_area']=='94118' and d['geo_matched']==1
    rich=next(p for p in d['properties'] if p['id']=='richmond-3')
    assert rich['geo_match'] is True and rich['geo_how']=='zip 94118'
    others=[p for p in d['properties'] if p['id']!='richmond-3']
    assert all(p['geo_match'] is False and p['verdict']=='Outside your area' for p in others)
    assert rich['rank']==1 and all(p['penalties']>=50 for p in others)

def test_geo_filter_landmark():
    d=run({'geo_area':'near Golden Gate Park'})
    matched={p['id'] for p in d['properties'] if p['geo_match']}
    assert matched=={'richmond-3','sunset-2'}
    rich=next(p for p in d['properties'] if p['id']=='richmond-3')
    assert 'Golden Gate Park' in rich['geo_how']

def test_geo_filter_neighborhood():
    d=run({'geo_area':'the mission'})
    assert d['geo_matched']==1
    m=next(p for p in d['properties'] if p['id']=='mission-3')
    assert m['geo_match'] is True and m['geo_how']=='neighborhood Mission'
    assert m['verdict']!='Outside your area'

def test_amenities_offline_seeded():
    d=run()
    for p in d['properties']:
        a=p['amenities']
        assert a['live'] is False and a['source_tag']=='assumption (seeded)'
        assert a['groceries']>0 and a['transit_stops']>0
        assert 'not public data' in a['shuttles']['note'] and a['shuttles']['source']=='assumption'

def test_amenities_live_merge(monkeypatch):
    monkeypatch.setattr(livedata,'amenities_for',lambda prop: {'groceries':21,'transit_stops':30,'parking':7,'bike_share':4})
    d=run()
    a=d['properties'][0]['amenities']
    assert a['live'] is True and 'OpenStreetMap' in a['source_tag']
    assert a['groceries']==21 and a['bike_share']==4
    assert '21 groceries' in a['summary']


def test_str_offline_seeded():
    c=TestClient(app)
    d=c.post('/api/analyze',json={}).json()
    for p in d['properties']:
        s=p['str']
        assert s['live'] is False
        assert s['source_tag']=='assumption (seeded)'
        assert '90 un-hosted nights' in s['summary']
        assert '14% TOT' in s['summary']
        assert len(s['rules'])==4


def test_str_live_merge(monkeypatch):
    monkeypatch.setattr(livedata,'str_comps',lambda neighborhood: {'median_nightly':300,'n_listings':50,'n_licensed':40,'snapshot':'June 2026'})
    c=TestClient(app)
    d=c.post('/api/analyze',json={}).json()
    s=d['properties'][0]['str']
    assert s['live'] is True
    assert s['source_tag'].startswith('Inside Airbnb')
    assert s['unhosted_ceiling_monthly']==round(300*90/12)
    assert '50 entire-home listings, 40 licensed' in s['summary']


def test_zori_offline_seeded():
    c=TestClient(app)
    d=c.post('/api/analyze',json={}).json()
    for p in d['properties']:
        b=p['rent_benchmark']
        assert b['live'] is False
        assert b['source_tag']=='assumption (seeded)'
        assert 'Zillow ZORI' in b['summary']


def test_zori_live_merge(monkeypatch):
    monkeypatch.setattr(livedata,'zori_benchmark',lambda zipcode: {'zori':4500,'month':'2026-08-31'})
    c=TestClient(app)
    d=c.post('/api/analyze',json={}).json()
    b=d['properties'][0]['rent_benchmark']
    assert b['live'] is True
    assert b['zori']==4500 and b['month']=='2026-08-31'
    assert '$4,500/mo' in b['summary']
