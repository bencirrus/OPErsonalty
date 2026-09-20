# SF OPE Homebase

Offline-safe hackathon vertical slice for the SF live-in multifamily property portal.

## Run

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000. Click "Run property team." The silicon-team run log and each specialist tile expand for details (what the role asks, its key evidence).

## What this proves

- One short intake drives a ranked property pitch.
- Ten visible specialist roles (Router / Orchestrator through Downside Reviewer) produce one decision surface; every role name carries a specialist title.
- The Reviewer removes unsupported rent from an unwarranted in-law, dropping Richmond coverage to 68% defensible and changing the winner.
- Spec ranking model: coverage, residual cash, cash-on-cash, owner-unit fit, evidence confidence, with subtractive penalties.
- Residual weekly cash is shown as a plain weekly picture; below-floor cases get a red flag, are excluded from recommended, and the language is "does not meet the floor you set" - never "you could make this work".
- Load-bearing claims carry source tags ([listing], [city-record], [market-comp], [assumption]); unverifiable claims render as VERIFY.
- Downside stress panel per property (vacancy, rent cut, rate shock).
- Approve / Pass / Send-back controls; approval writes local status only.

## Evidence boundary

Property names, prices, rents, costs, and renovation findings are seeded demo data - not real listings or advice. The seeded street addresses are fictional listing data chosen so the live record check is meaningful.

Two adapters pull live public data (no API key; keyless throttled tier):

- `livedata.py` -> SF DBI Building Permits (`i98e-djp9`) and Rent Board Housing Inventory (`gdc7-dmcn`) on data.sfgov.org, checked per seeded address by the Permit & Zoning Analyst. Live wins over seeded where they disagree; the override is shown on the brief.
- `livedata.py` -> FRED MORTGAGE30US via `fredgraph.csv` for the financing rate; the intake rate field is pre-filled from it.

Offline behavior: any failure (network, throttle, schema change) falls back to the seeded record and the seeded 6.75% rate, and the page shows `seeded (offline)`. Results are cached in `.livedata-cache.json` (6h TTL) so demo runs stay polite to the keyless tier. Tests never touch the network - the HTTP layer is mocked.

## Static Pages snapshot

`python bake_site.py` re-bakes `../index.html` + `../site-assets/` from the app's live output. The static page keeps its snapshot labeling; its form does not recompute.
