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

## Read the repository first

This file deliberately does **not** record the active branch, commit hashes, or
the state of anyone's working tree. That information is machine-local, goes
stale within hours, and git already answers it precisely:

```bash
git status && git branch --show-current && git log --oneline -10
```

Where this file disagrees with the repository, the repository is right.

---

## Current task

Product design only; no code in flight. The context-document restructure this
section used to describe is finished and published, so it has left this file.

A design pass on a criteria-based score ran to a stopping point without touching
code. The stakeholder input behind it, and the questions it left open, are in
[`product-discovery.md`](product-discovery.md). **What the pass concluded is not
recorded anywhere in this repository** — deliberately, because none of it was
accepted as a decision record. A fresh session will find the inputs and the open
questions, but not the reasoning between them.

## Released

Latest release: `v2.0.1`. See [`../README.md`](../README.md) for shipped
capabilities.

## In progress

**Check a draft before publishing.** Implemented, unreleased. Its usefulness is
under review rather than settled — the checks are thinner than the reporting
frame around them. See [`product-discovery.md`](product-discovery.md).

**Turkish interface edition.** Uncommitted, and not ready to land.

- Working: negotiation is `X-Aether-Language` → `Accept-Language` → Turkish;
  every user-facing surface has Turkish wording; the manual TR/EN switcher
  persists to `localStorage` and beats the browser preference.
- Not yet consistent: about half the translations are second lookup tables as
  designed. The rest are inline `if language is TURKISH else` ternaries and
  dicts rebuilt inside function bodies — roughly twenty in the plain-text
  renderer, four in `_report_view`, two helpers in
  `editor_recommendation_text.py`. The four in `_report_view` violate
  [decision 0007](decisions/0007-separate-finding-codes-from-wording.md) and are
  the reason this has not landed.
- The interface language module is not yet part of the committed tree.

## Blockers

| Blocker | Blocks | Needs |
|---|---|---|
| No answer on what "duplicate" means | Any duplicate-detection work | Q1 and Q6 in [`product-discovery.md`](product-discovery.md) |
| No real TRT Dinle page captured | Any non-article content model | A sample export or public URLs (Q11–Q12) |
| Corpus is in-memory and process-scoped | Every cross-item finding | Persistence behind `ContentRepository` — see [`architecture.md`](architecture.md) |
| Browser verification is manual | Regressions in the page script | See **Verification** |

Product direction is blocked on discovery, not on code. Nothing above blocks
ordinary bug-fixing.

## Verification

| Level | Status |
|---|---|
| **tests pass** | Yes — 208 tests |
| **served-page verified** | **No** — the app has not been exercised in a browser against the in-progress work |
| **feature complete** | **No** — the Turkish edition has not landed |

Why a green suite is weaker than it looks — the structural reasons — is recorded
in [`architecture.md`](architecture.md). The vocabulary is in
[`../AGENTS.md`](../AGENTS.md) §3.

## Next actions

In order.

1. **Re-add `<p id="outcome-happened"></p>` to the outcome card** in
   `index.html` before the Turkish edition lands. The i18n pass removed it while
   the page script still assigns to it, so the outcome explanation cannot
   render. Verify by starting the app and analysing a non-article URL, not by
   reading the template.
2. **Teach the page-script harness to fail on this class of bug**: return `null`
   for selectors the template does not declare, and make `querySelectorAll`
   match. Own branch, own commit. This converts a whole regression class from
   invisible into a test failure.
3. **Reconcile the language defaults.** `language.py` documents Turkish as the
   default and fallback, but 21 Python signatures default to `Language.ENGLISH`.
   No current caller reaches them, because the HTTP boundary always passes a
   resolved value; the first one that does will get the wrong language silently.
4. **Then** the inline-ternary cleanup in `_report_view` and the plain-text
   renderer, which is what decision 0007 requires before this lands.

Do not merge and do not tag any of this without being asked.
