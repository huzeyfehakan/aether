# Handoff — current state

Volatile state only: what is being worked on, what is blocking it, what is
verified right now, and what to do next. Anything that outlives the current
piece of work belongs elsewhere.

- **How to work** → [`../AGENTS.md`](../AGENTS.md)
- **Which file to read when** → [`context.md`](context.md)
- **Why it works this way** → [`decisions/`](decisions/)
- **What we do not know yet** → [`product-discovery.md`](product-discovery.md)
- **How the code is arranged, and its long-lived constraints** →
  [`architecture.md`](architecture.md)

## Current task

Prepare the existing product documentation for final handoff. Application
behaviour is unchanged in this documentation-only work.

## Released

Latest tagged release: `v2.0.1`. The current handoff branch contains additional
work after that tag; its delivered state is described below.

## Delivered state

- Turkish-first presentation is committed. Turkish is the default and fallback;
  the TR/EN switcher persists a valid choice and rerenders retained results.
- Published URL analysis and draft analysis expose deterministic SEO and GEO
  score dimensions. Score details are rendered inside their owning cards.
- Discoverability's Unique Target Ratio is calculated as unique **body** targets
  divided by body links, rather than using page-wide targets or links.
- Editor recommendations include related-passage attribution where the
  underlying recommendation has identifiable source passages.
- Draft GEO is presented as a pre-publication preview ("Yayın Öncesi GEO
  Önizlemesi"). Draft and published-page GEO are not directly comparable because
  their measurable signal sets differ; unavailable draft dimensions remain
  unmeasured.
- The experimental revised-content / what-if GEO scenario was evaluated and
  intentionally rolled back. It is not part of the delivered product.

The current branch is synchronized with origin at `dabb815`.

## Blockers

No implementation blocker is recorded for the delivered handoff state.

## Verification

| Level                    | Status                                                                      |
| ------------------------ | --------------------------------------------------------------------------- |
| **tests pass**           | Yes — ran 354 tests: `OK (skipped=22)` |
| **served-page verified** | Not fully verified locally — Node was unavailable, so Node-dependent browser/presentation tests were skipped |
| **feature complete**     | Delivered functionality is present; the skipped browser paths remain explicitly unverified locally |

`git diff --check` passed during final local verification.

Why a green suite is weaker than it looks — the structural reasons — is
recorded in [`architecture.md`](architecture.md). The vocabulary is in
[`../AGENTS.md`](../AGENTS.md) §3.

## Next actions

1. Run the Node-dependent presentation/browser tests in an environment with
   Node available.
2. Perform any final stakeholder acceptance review required before release or
   merge; do not reintroduce the rolled-back revised-content scenario without a
   new product decision and evidence.
