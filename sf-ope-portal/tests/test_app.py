from fastapi.testclient import TestClient
from app import app
c=TestClient(app)
def test_unwarranted_unit_changes_ranking():
 d=c.post('/api/analyze',json={}).json(); ps=d['properties']
 rich=next(p for p in ps if p['id']=='richmond-3')
 exc=next(p for p in ps if p['id']=='excelsior-2')
 assert rich['verified_rent']==6400 and rich['coverage']==68
 assert exc['rank']<rich['rank']
 assert exc['coverage']==107 and exc['residual']==118
 assert exc['rank_reason']=='Recommended'
 assert 'UNWARRANTED UNIT' in rich['risk']
def test_floor_blocks_recommendation():
 d=c.post('/api/analyze',json={'min_living_allowance_usd_per_week':200}).json()
 assert all(p['rank_reason']!='Recommended' for p in d['properties'] if p['residual']<200)
