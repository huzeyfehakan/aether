# 0007 — Separate finding codes from their wording

## Decision

The application layer decides *whether* a finding applies and emits a **code**, a
category, and the supporting facts — never a sentence. Presentation decides *how
it reads*, and in which language.

## Why

Copy inside a use case fixes the report to one language and puts copywriting
into business logic.

The reverse is worse: presentation deciding *whether* a finding applies would
put a business rule where no test of the application layer can reach it.

## Evidence and context

- `derive_editor_recommendations.py` is the single place a measurement becomes
  advice. `build_draft_review.py` does the same for drafts, emitting
  `DraftCheck` and `UnavailableCheck` codes.
- Wording lives in `editor_recommendation_text.py`, `draft_check_text.py` and
  `page_outcome_text.py`.

## Consequences

- A new finding needs a code, a category, and a wording entry per supported
  language ([0006](0006-turkish-is-the-default-interface.md)).
- Wording changes never require an application-layer test to change.

## Known violation

This decision is currently violated in one place, `_report_view` in
`presentation/web/app.py`. The violation is tracked as open work in
[`../handoff.md`](../handoff.md); the detail is not repeated here.

## Reopen when

Not as a convenience. This is the rule that makes both the audience split
([0004](0004-every-finding-names-who-can-act.md)) and the language decision
testable.
