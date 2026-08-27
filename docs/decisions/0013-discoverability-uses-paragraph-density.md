# Discoverability score uses paragraph-based density saturation

## Context

The Discoverability score previously calculated the proportion of outgoing links retained in the article body (`body_links / outgoing_links`). However, evaluating a proportion heavily penalizes publishers with extensive site-wide navigation (e.g. mega-menus), where the denominator is arbitrarily large and out of the editor's control.

A better proxy for whether an article is sufficiently discoverable via its body is the absolute density of links placed within the text the editor controls.

## Decision

- Change the discoverability score formula to rely on `body_link_density`.
- `body_link_density = body_link_count / total_passage_count`.
- To bound this to a 0-100 score, use a saturation function: `score = (density / (1 + density)) * 100.0`.
- Display the density as a `MEASUREMENT` without percentage scaling.

## Consequences

- The denominator is now bounded by the article's own structure, giving editors direct control over the score.
- **Discontinuity note**: Discoverability scores generated before this change are not comparable to new scores. Same-article comparisons crossing this change boundary will show sudden shifts.

## Reopen when

If we gather evidence that passage count is a poor denominator (e.g. short listicles vs long essays) or if the saturation curve is too generous/punishing for typical SEO guidelines.
