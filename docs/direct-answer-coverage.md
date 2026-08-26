# Direct Answer Coverage

Direct Answer Coverage is an experimental diagnostic and is not included in
the GEO score. It is a deterministic, question-heading-scoped proxy for answer
extractability. It classifies a small explicit set of Turkish and English
question forms, pairs each measurable heading with its first eligible article
passage, and checks bounded answer-type cues behind a boolean lexical relevance
guard.

No measurable supported question headings produce `None`; measurable headings
with no recognized direct answers produce `0.0`; partial and complete coverage
remain ratios between those values. None of these values affects Semantic
Completeness or the final GEO score.

The metric was removed from its inherited `0.30` Semantic Completeness slot
after diagnostic benchmarking found realistic false negatives, systematic
cue-word false positives, insufficient labeled-corpus calibration, and enough
score leverage to move final GEO by roughly 8–14 points in the benchmark
scenarios. Those findings remain characterization evidence, not a production
threshold or accuracy target.

The metric is not a claim that generative engines use this exact formula.
Scored use may be reconsidered only after precision and recall are evaluated on
a manually labeled corpus.

Known limitations:

- It uses lexical and relation heuristics rather than deep semantic inference.
- Its Turkish and English question and answer rules are intentionally limited.
- It does not use stemming, an LLM, or an external service.
- False positives and false negatives remain possible, especially when an
  answer uses synonyms or morphology that shares no normalized heading token.
