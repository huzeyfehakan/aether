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

The current work revolves around safely handling CSR (Client-Side Rendered) articles. When Aether fails to see the body (e.g. because Nuxt/React hydration hasn't occurred and the HTML contains empty containers), it was silently reporting 0 for body-dependent SEO and GEO dimensions, severely misrepresenting the page. We have implemented "fail loud" detection and suppressed body-dependent scores for unreliable captures (Decision 0012).

## Released

Latest release: `v2.0.1`. See [`../README.md`](../README.md) for shipped
capabilities.

## In progress

**Proportional Dual Scoring (SEO/GEO) & Unreliable Body Safety** Implemented, unreleased.
- Unreliable body captures (CSR pages) are now detected via `page_visible_word_count` and `empty_body_block_count`.
- `BODY_NOT_SERVER_RENDERED` or `INCOMPLETE_BODY_CAPTURE` is yielded.
- Body-dependent GEO/SEO dimensions and recommendations are suppressed if unreliable.
- A UI warning is surfaced to the user.

**Turkish interface edition.** Uncommitted, and not ready to land.
- Not yet consistent: about half the translations are second lookup tables as
  designed. The rest are inline `if language is TURKISH else` ternaries and
  dicts rebuilt inside function bodies.

## Blockers

Nuxt 2 payload extraction (Stage 4). TRT uses an IIFE (`window.__NUXT__=(function(...){...}(...));`) instead of a JSON literal. `json.loads` cannot parse this natively, and executing JS is prohibited. We need to decide whether to implement a generic JS parser, use Regex for string literals, or defer Nuxt 2 IIFE support.

## Verification

| Level                    | Status                                                                      |
| ------------------------ | --------------------------------------------------------------------------- |
| **tests pass**           | Yes — 232 passed, 6 skipped                                                 |
| **served-page verified** | Yes — Verified that `BODY_NOT_SERVER_RENDERED` correctly suppresses scores on CSR fixtures. |
| **feature complete**     | No — Nuxt 2 IIFE extraction remains unimplemented due to `json.loads` constraint. |

## Next actions

1. Re-evaluate the Nuxt 2 payload extraction (Stage 4). The user requested extraction via `json.loads` without `eval`, but the payload is a JS IIFE. Needs product alignment on how to parse it.
2. Address the "Anlamsal Bütünlük" metric flaw (penalizes capturing short passages and creates a perverse incentive) which was surfaced during the BULGU-0 debugging.
3. Clean up the remaining Turkish language presentation inconsistencies.
