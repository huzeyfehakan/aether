# Breakdown items are typed as scores, ratios, or counts

## Context

Editor recommendations and analysis breakdown panels previously displayed all metric components (`ScoreSignalDetail`) with the same decimal format (e.g., `97.0 / 100`). However, these elements represent different types of values:

1. **Counts**: Raw integers like outgoing links (`4,655`).
2. **Ratios**: Percentages like target ratios or densities (`55.6%`).
3. **Scores**: Weighted or bounded 0-100 dimensions (`62.5 / 100`).
4. **Measurements**: Raw floating point limits, scales, or densities (e.g. `4.3`).
5. **Context**: Values not used in the score calculation directly, but shown to aid editor comprehension (e.g., `unique targets`).

Treating raw counts like `108` as a score `108.0 / 100` violates the principle of separation between measurement and score, misleading users to think they scored >100 on a metric or confusing them about the scale.

## Decision

- Add type metadata (`kind: SignalKind = SCORE | RATIO | COUNT | MEASUREMENT`) to `ScoreSignalDetail`.
- Add `is_context: bool` to explicitly separate scoring inputs from context inputs.
- Renderers (Markdown, PlainText, HTML) must evaluate `kind` and format correctly:
  - `SCORE`: Show out of 100 (e.g. `62.5 / 100`)
  - `RATIO`: Show as percentage (e.g. `%55.6`)
  - `COUNT`: Show as localized whole integer (e.g. `4,799`)
  - `MEASUREMENT`: Show as raw decimal (e.g. `4.3`)
- Contextual variables (`is_context=True`) must be visually distinct in interfaces to clarify they do not directly penalize or boost the score.

## Consequences

- Breakdowns now clearly state their unit format, preventing "108 / 100" anomalies.
- Renderers are slightly more complex but semantically accurate.

## Reopen when

If a new measurement requires a fundamentally different visualization beyond simple numbers (e.g., semantic categories, confidence intervals, lists).
