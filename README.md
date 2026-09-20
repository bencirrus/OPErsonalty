# SF OPE Homebase

A portal where a team of specialist agents analyzes San Francisco multifamily buildings for a one-person entrepreneur: find the property you can live in while the other units' rent covers your housing costs.

Built for the Carbon-Silicon Hackathon "one-person entrepreneur" theme: one carbon entrepreneur, one silicon team doing the analyst work.

**Live demo: https://bencirrus.github.io/OPErsonalty/** - a static snapshot of the seeded demo. The form inputs don't recompute there; the full app runs locally (below).

## The demo in one line

Four seeded buildings go in, twelve specialist roles check rents, layouts, permits, repairs, financing, and downside, and the Downside Reviewer catches an unwarranted in-law unit - stripping its unsupported rent drops the Richmond triplex from 105% claimed coverage to 68% defensible, and a legal duplex takes the top spot.

## What's here

- `sf-ope-portal/` - the vertical slice: FastAPI app, intake schema, ten specialist roles (Router / Orchestrator, Acquisition Scout, Rent-Roll Analyst, Layout & Owner-Unit Analyst, Permit & Zoning Analyst, Construction & Repair Estimator, Renovation Feasibility Planner, Financing Analyst, OpEx & Tax Analyst, Downside Reviewer), ranked pitches with evidence and risk tags, tests. See `sf-ope-portal/README.md` to run it.
- `index.html` + `site-assets/` - the static snapshot served by GitHub Pages, with the real analysis output baked in.

All property data is seeded demo data, not real listings or advice. Live listing, permit, rent-comp, and financing adapters plug into the same API shape later.

## How this repo is built

The repo itself is the workflow being demoed: a human directs, an agent executes, and commits land as [`instinct-swe`](https://github.com/instinct-swe), a repo-scoped machine account with its own credentials. Every commit on `main` is bot-authored.
