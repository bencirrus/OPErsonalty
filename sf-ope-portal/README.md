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
- Ten visible specialist roles (Router through Downside Reviewer) produce one decision surface.
- The Reviewer removes unsupported rent from an unwarranted in-law, dropping Richmond coverage to 68% defensible and changing the winner.
- Spec ranking model: coverage, residual cash, cash-on-cash, owner-unit fit, evidence confidence, with subtractive penalties.
- Residual weekly cash is shown as a plain weekly picture; below-floor cases get a red flag, are excluded from recommended, and the language is "does not meet the floor you set" - never "you could make this work".
- Load-bearing claims carry source tags ([listing], [city-record], [market-comp], [assumption]); unverifiable claims render as VERIFY.
- Downside stress panel per property (vacancy, rent cut, rate shock).
- Approve / Pass / Send-back controls; approval writes local status only.

## Evidence boundary

All property names, prices, records, financing, rents, costs, and permit findings are seeded demo data. They are not real listings or advice. Live listing, SF DBI/PIM/Open Data, rent-comp, and financing adapters belong behind the same API shape after repo and data-source decisions are known.
