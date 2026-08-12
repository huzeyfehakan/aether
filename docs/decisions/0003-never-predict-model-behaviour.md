# 0003 — Never predict model behaviour

## Decision

Aether reports what is on the page and what that costs a system reading it. It
does not state, estimate, or score how any AI system will rank, quote, retrieve,
or answer from the page.

## Why

Model behaviour is not observable from the page, changes without notice, and
differs per system. A claim about it could not be verified when an editor
challenged it, and would turn a deterministic report into a forecast.

## Evidence and context

- No model is called anywhere in the pipeline. Every finding is derived from the
  page by fixed rules.
- **Rejected — a numeric readiness score.** It would compress unrelated facts
  into one number and would read as a prediction of visibility.
- `AssessAIReadiness` produces one three-value classification of metadata
  completeness (`complete | partial | missing`) and nothing else.

## Consequences

- **AI readiness and AI visibility are different concepts.** Readiness is a
  property of the page. Visibility — whether an AI system actually cites TRT —
  is an outcome in the world, observable only by watching those systems, and is
  out of scope under this decision.
- "AI Readiness" as an *editor-facing* name promises more than the product
  delivers and invites the one question this decision refuses to answer. The
  naming question is open and is recorded in
  [`../product-discovery.md`](../product-discovery.md), not here.

## Reopen when

Not under the current product framing. A visibility product would be a separate
product with a separate determinism contract, not an extension of this one.
