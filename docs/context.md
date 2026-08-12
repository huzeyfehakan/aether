# Context index

**Navigation only.** Which document to read, for which task, in which order.

The rules that govern what may be *written* into each document are in
[`../AGENTS.md`](../AGENTS.md) §6, not here.

## Where things live

| Document | Go here for |
|---|---|
| [`../AGENTS.md`](../AGENTS.md) | How to work: session startup, git, verification, context maintenance |
| [`handoff.md`](handoff.md) | What is being worked on right now, what blocks it, what to do next |
| [`decisions/`](decisions/) | Why a rule is the way it is, and what would reopen it |
| [`product-discovery.md`](product-discovery.md) | What is still unknown, unconfirmed, or waiting on a stakeholder |
| [`architecture.md`](architecture.md) | Layers, domain concepts, package map, long-lived technical constraints |
| [`../README.md`](../README.md) | What the product does, from a user's point of view |

## Reading order by task

### Starting a coding session

1. [`../AGENTS.md`](../AGENTS.md) — the rules, in full.
2. [`handoff.md`](handoff.md) — where the work stands.
3. Inspect the repository yourself and reconcile it against the handoff. The
   repository wins.
4. [`decisions/`](decisions/) — the records touching what you are about to
   change. Do not skip this: it records what has already been tried and
   measured.
5. [`architecture.md`](architecture.md) — its **Domain concepts** section before
   you read `domain/` or `application/` for the first time; the package map when
   adding or moving a module.

### Starting a product-discovery session

1. [`product-discovery.md`](product-discovery.md) — what is known, assumed and
   unknown.
2. [`decisions/README.md`](decisions/README.md) — the constraints any proposal
   has to survive, and the ideas already rejected with evidence.
3. [`handoff.md`](handoff.md) — only for what is currently broken or blocked.

Do not read `architecture.md` first in a discovery session. It describes the
solution that exists, which is the thing under question.

### Fixing a bug

1. [`handoff.md`](handoff.md) — it may already be recorded, with its cause.
2. [`../AGENTS.md`](../AGENTS.md) §3 — what counts as verified. A green test
   suite is not browser verification, and
   [`architecture.md`](architecture.md) explains why the suite is weaker than it
   looks.
3. The decision record for the rule involved, if the bug is in a finding rather
   than in plumbing.

### Answering "why does it work this way?"

[`decisions/`](decisions/) first, then the module docstring — several modules
carry their own reasoning, including `declared_text_comparison.py`,
`analyze_heading_structure.py` and `assess_page_content.py`. Extraction
contracts have separate notes:
[`body-extraction.md`](body-extraction.md),
[`publication-date-extraction.md`](publication-date-extraction.md).

## What is not written down anywhere

TRT's real content taxonomy, and what TRT means by "duplicate". Both are
deliberately absent rather than guessed. See
[`product-discovery.md`](product-discovery.md).
