# 0012: Gövde Güvenilir Okunamadığında Skor Üretilmez

- **Date:** 2026-08-25
- **Status:** Accepted
- **Impacts:** Analysis domain, web presentation

## Decision

When Aether detects that it cannot reliably read the full body text of an article (due to client-side rendering or non-standard DOM nesting that results in dropped paragraphs), it will explicitly mark the body capture as unreliable (`body_capture_is_reliable = False`). Any GEO or SEO score dimension that relies on body text (Semantic Completeness, Entity Authority, Structural Richness, Semantic Quality, etc.) will be suppressed and output as `None`. Furthermore, any editor recommendations dependent on body parsing (e.g. `NO_STATISTICS`, `NO_CITATIONS`, `CONTENT_BLOAT`, `WEAK_ARTICLE_OPENING`, etc.) will also be suppressed.

## Reason

Aether is an AI reading readiness tool, and its primary job is to show publishers what an AI crawler sees. If a crawler (like Googlebot without JS execution, or smaller AI scrapers) fails to see the body, presenting scores based on the empty or drastically truncated text is highly misleading. For example, a 900-word article could be scored as having "0% statistics" and "0% citations" simply because Aether only managed to parse 55 words of footer links. "Ölçemediğin şeye skor verme" (Do not score what you cannot measure) is a safer failure mode than hallucinating failure metrics.

## Alternatives Considered

- **Headless Browser Rendering**: Executing JavaScript to evaluate CSR pages. Rejected because it contradicts Aether's mission. AI crawlers have wildly varying JS execution capabilities, and Aether's job is to enforce "deterministic HTML readiness", not to emulate a full browser.
- **Scoring 0% Instead of None**: Rejected because it misleads the publisher into thinking their content lacks quality, rather than recognizing that their content lacks technical accessibility.

## Reopens if

- A robust, generic, JS-free extraction mechanism is discovered that guarantees 100% parity with what users see on all major CSR frameworks.
