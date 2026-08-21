# 0010 - Dual Scoring System (Supersedes 0003)

## Decision

Aether calculates and displays two distinct composite scores (0-100): an **SEO Score** and a **GEO (Generative Engine Optimization) Score**.

This decision supersedes [0003 (Never predict model behaviour)](0003-never-predict-model-behaviour.md) regarding the rejection of numerical scores. We now embrace numerical composite scores, provided they are deterministic measurements of page structure and content, not predictions of model behaviour.

## Why

The original rejection of a numeric readiness score (0003) was based on the premise that compressing unrelated facts into one number reads as a prediction of visibility.

However, product feedback and the industry shift toward Generative Engine Optimization (GEO) demonstrated that editors need a quantifiable way to track progress. A binary or purely qualitative report is hard to action across a newsroom.

By separating SEO (traditional metadata, structured data, semantic quality, and technical access) from GEO (semantic completeness, entity authority, structural richness, and discoverability), we provide a framework that measures *readiness* without predicting *visibility*. The score is a mathematical reduction of deterministic checks (e.g., presence of statistics, citations, outbound links, schema.org declarations), not an AI hallucination.

## Evidence and context

- **GEO vs SEO Split:** Traditional SEO focuses on crawlers (metadata, tags). GEO focuses on LLMs and RAG systems (entities, statistics, explicit declarations, and earned media). Combining them creates conflicting incentives. Separating them allows editors to optimize for the distinct requirements of AI Answer Engines (ChatGPT, Gemini, Perplexity).
- **Deterministic Metrics:** The GEO score relies on strict, parser-driven metrics (e.g., `body_link_count / outgoing_link_count`, schema.org `author` / `publisher` presence) instead of arbitrary regex heuristics.
- **Fail Toward Silence:** In accordance with [0005](0005-fail-toward-silence.md), missing or unmeasurable data paths (e.g., a missing duplication analysis) do not yield `0.0` or `100.0`. They are evaluated as `None`, and the composite score dynamically recalculates its total using only the available weight percentages, preventing false penalties or free points.
- **Earned Media Multiplier:** Entity Authority leverages outbound domains not as a base score, but as a bounded multiplier (up to 20%), rewarding real external citations while ignoring social media links.

## Consequences

- The application layer must maintain mathematical rigor when calculating totals to handle missing analysis components gracefully (`Optional[float]`).
- Future additions to the scoring logic must be deterministic and transparently weighted. Arbitrary constants without a verifiable basis are not allowed.
- The UI displays scores alongside the specific factors that compose them, ensuring the score is always explained by its parts.

## Reopen when

The industry consensus on Generative Engine Optimization (GEO) metrics changes substantially, or if the current 0-100 normalization proves too rigid to accommodate new types of deterministic structural checks.
