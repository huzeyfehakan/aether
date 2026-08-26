# Passage Balance

Passage Balance is an experimental structural diagnostic:

```text
mean(passage word counts) / max(passage word counts)
```

The measurement is deterministic, but it is sensitive to HTML paragraph
segmentation and to non-article paragraphs entering the passage population.
The same prose can therefore produce different values when its paragraph
boundaries change. A low value can also result from a legitimate mixture of
short duration/details passages and longer explanatory passages, without any
oversized passage.

Passage Balance is retained for observation but is not included in Semantic
Completeness or any other score. Aether makes no claim that uniform paragraph
length directly predicts retrieval, citation, or generative-engine visibility.

Oversized Passage Rate remains a separate experimental diagnostic; it is not a
validated replacement. Any future passage-quality score should be calibrated
against measured retrieval and citation outcomes before affecting GEO.
