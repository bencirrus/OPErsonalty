# SF OPE Homebase

Offline-safe hackathon vertical slice for the SF live-in multifamily property portal.

## Run

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000. Click "Run property team."

## What this proves

- One short intake drives a ranked property pitch.
- Eight visible specialist roles produce one decision surface.
- The Reviewer removes unsupported rent from an unwarranted in-law, dropping Richmond coverage from 105% claimed to 68% defensible and changing the winner.
- The user's weekly living-cash floor is explicit. Below-floor cases are high risk and never recommended.
- Load-bearing claims show evidence confidence and warning tags.

## Evidence boundary

All property names, prices, records, financing, rents, costs, and permit findings are seeded demo data. They are not real listings or advice. Live listing, SF DBI/PIM/Open Data, rent-comp, and financing adapters belong behind the same API shape after repo and data-source decisions are known.
