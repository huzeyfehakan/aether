# Project handoff

State at `v2.0.1`. Implementation is complete; further work should be driven by
feedback from real editors rather than by adding checks.

## Architecture

Ports and adapters, dependencies pointing inward.

```text
domain/         Immutable records and their invariants. Knows nothing else.
application/
  ingestion/    Raw HTML to an immutable article version
  analysis/     Measurements, and the advice derived from them
ports/outbound/ Repository contracts
adapters/       HTTP fetching, in-memory repositories
presentation/   Renderers, editor-facing wording, FastAPI app
```

Two rules shape the code more than the diagram does:

- **`derive_editor_recommendations.py` is the only place a measurement becomes
  advice.** It emits a recommendation *code*, a category naming who can act on
  it, and supporting facts — never a sentence.
- **Presentation decides how a finding reads, never whether it applies.**
  Wording lives in `editor_recommendation_text.py` so copy stays out of use
  cases, and so a Turkish edition is a second table rather than a rewrite.

## Design principles

1. **Deterministic, with no thresholds.** Where a rule needs a comparison it
   compares two measured quantities, never a chosen constant. A body is
   "mostly boilerplate" when its shared words outnumber its own — not when it
   falls under a length.
2. **No publisher-specific rules.** Nothing keys on a name, host or URL.
3. **Never predict model behaviour.** The product reports what is on the page
   and what that costs. It does not say what an AI system will do.
4. **Every finding is addressed to someone.** Editor or technical. A finding
   nobody can act on does not belong in the report; several measurements were
   deleted for failing that test.
5. **Fail toward silence.** A false positive costs an editor's trust; a missed
   finding costs less. Rules are built to err that way, and which way each errs
   is documented.

## Intentionally rejected

Recorded beside the rules that replaced them, so they are not re-proposed:

- **`og:type` for classifying pages.** Wrong in both directions on TRT: a video
  page declares `article`, a news article declares `website`.
- **"This article has no subheadings."** Cannot be stated without a length
  threshold; the boundary is a judgement about writing.
- **Matching any title fragment against any other.** Two different headlines
  sharing a site name would agree.
- **A numeric readiness score.** Deliberate from the outset.
- **Duplicate titles, image alt-text, FAQ detection.** No evidence of
  occurrence, or no recommendation produced. TRT alt-text measured 6/6, 11/15,
  75/78.
- **`skipped_heading_levels`,** withdrawn after shipping: it found template
  furniture, not outline faults, on four of six pages.

## Known limitations

- Cross-article findings (repeated text, mostly-boilerplate body) hold only for
  the current process. Persistence behind the repository port is the single
  change that would most increase how often they fire.
- Template-level findings are reported per article, so one fix is restated on
  every article of a property.
- Title comparison has documented edge cases, chiefly breadcrumb titles.
- `EditorRecommendation` carries eight optional fields; typed variants per kind
  would be cleaner.
- CI does not execute the page script. Two regressions came from that seam.

## What to change, and what not to

**Do not change:** the determinism contract; the refusal to predict model
behaviour; the audience split; the separation of recommendation codes from
wording; the `v1.0.0` tag.

**Worth changing when reopened:** `_report_view` in `web/app.py` — a single
large dict literal, and the site of both frontend/backend regressions.
Persistence behind `ContentRepository`. Property-level reporting for template
findings. A CI smoke test that runs the page script.

## First questions when editor feedback arrives

1. Which recommendations did editors act on, and which did they scroll past?
   Anything consistently ignored should be removed, not reworded.
2. Was anything dismissed as "not my job"? That means the audience split is
   wrong for that finding, not that the finding is wrong.
3. Did any finding turn out to be false? Trace it to the rule and check which
   direction that rule was built to err in.
4. What did an editor want to know that the report does not say? That is the
   only sound source of a new capability.
5. **Do TRT editors control per-article structured data in the CMS, or only
   engineering?** This was flagged early and never confirmed. If editors do
   control it, several findings currently filed under technical belong to
   them, and the split needs revisiting.
