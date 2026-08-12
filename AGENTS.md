# AGENTS.md — working instructions for coding agents on Aether

Aether reports what is on a publisher's page and what that costs an AI system
reading it. It does not predict model behaviour and it does not score.

This file is the permanent rulebook: **how to work**. It applies to any coding
agent and does not change from session to session.

It does not record project state, product decisions, or open questions. Those
live elsewhere — [`docs/context.md`](docs/context.md) says which file holds
what, and is the shortest thing to read if you are unsure.

---

## 1. Session startup

Do this before touching anything, every session. Assume no previous
conversation exists and nothing carries over.

1. **Read this file.**
2. **Read [`docs/handoff.md`](docs/handoff.md)** — the current state.
3. **Inspect the repository yourself:**
   ```bash
   git status
   git branch --show-current
   git log --oneline -10
   git rev-list --left-right --count main...HEAD
   git for-each-ref --sort=creatordate --format='%(refname:short)' refs/tags
   ```
4. **Reconcile the handoff against what you found.** Do not trust it blindly.
   It records a state that was true at a past commit. Where the handoff and the
   repository disagree, **the repository is right** — correct the handoff, and
   say what was stale. Do not guess which one was intended.
5. **Read the relevant records in [`docs/decisions/`](docs/decisions/)** before
   changing analysis behaviour. They record what has already been tried and
   measured, so an idea is not re-proposed without new evidence.
6. **Report the current state briefly** before starting implementation: branch,
   commit, working tree, test status, and anything that contradicts the handoff.
7. **If the task is unclear, ask before changing code.** A wrong guess costs
   more than a question.

---

## 2. Git workflow

**Branching**

- Work on a branch named for the unit of work: `feat/…`, `fix/…`,
  `refactor/…`, `chore/…`, `docs/…`.
- Do not work directly on `main` unless explicitly instructed to.
- One coherent unit per branch.
- Old branches are historical. Do not resume one because it exists. The branch
  the handoff names as active is the authoritative location of unfinished work.

**Committing**

- Commit after each coherent, verified unit of work. Do not wait until an
  entire feature is finished and land it as one large commit.
- Equally, do not produce meaningless micro-commits. A commit should stand on
  its own and be describable in one line.
- Convention: a conventional prefix with an optional scope and a lowercase
  imperative subject, for example
  `fix(web): clear the loading state where the button is re-enabled`.
- **Do not add agent or co-author attribution to commits.** No
  `Co-Authored-By`, no generated-by trailers. Commits carry only the
  repository's configured Git identity.

**History and releases**

- **Never rewrite published history.** Check what is on `origin` before
  rebasing or amending: `git fetch`, then compare against the upstream ref.
- **Never move or rewrite an existing release tag.**
- **Never merge to `main` unless explicitly asked to merge.**
- **Never create a release tag unless explicitly asked to release.**

---

## 3. Verification

Three things are distinct. Never let one stand in for another, and always say
which one you actually achieved:

| Level | Means |
|---|---|
| **tests pass** | The test suite ran green |
| **served-page verified** | The running application was exercised through the real served page |
| **feature complete** | The intended user flow works end to end |

Rules:

- **Passing Python tests is never browser verification.** Do not describe it as
  such, and do not imply it. This repository has a documented history of
  regressions that shipped with a green suite.
- For web or UI changes, verify against the **real served page** whenever
  practical — start the app and exercise the flow. Reading the template is not
  verification.
- For JavaScript changes, verify the execution path in a browser or JavaScript
  runtime, not the template text.
- Give every real regression that reached the browser a regression test when
  practical.
- **If browser or Node verification is unavailable, say so explicitly** and
  name what is therefore unverified. Silence reads as "verified".

Run the suite with:

```bash
python -m unittest discover -s tests
```

The project uses `unittest`; pytest is not installed and CI does not use it.
Some tests require Node and skip silently without it — check the skip count,
not just the `OK`. Run the suite inside the project's virtual environment; a
bare system interpreter may not carry the dependencies.

---

## 4. Engineering principles

- **Prefer fixing incorrect existing behaviour over adding capability.**
- **Do not introduce speculative heuristics or features** because they seem
  useful. New capability should come from actual editor feedback or a
  demonstrated product need.
- **The product's standing decisions live in [`docs/decisions/`](docs/decisions/)**,
  each with the evidence behind it and the condition that reopens it. Read the
  relevant ones before changing a rule. Do not weaken one silently: use its
  stated reopening condition, or open a new record superseding it.
- **Do not record an unverified belief as a decision.** If it is not confirmed,
  it belongs in [`docs/product-discovery.md`](docs/product-discovery.md),
  labelled.

---

## 5. Session completion

Before ending a substantial session:

1. Run the appropriate verification and record the result honestly.
2. Inspect `git status`.
3. Commit the meaningful completed work.
4. **Update [`docs/handoff.md`](docs/handoff.md)** — and only the handoff — with
   the new project state.
5. Record there: open work, open defects, blockers, verification status, and the
   recommended next step. Keep it to what survives a fresh clone; leave branch,
   commit and working-tree detail to git.
6. **State clearly what was not done** — skipped scope, unverified paths,
   deferred decisions.
7. If work is intentionally left uncommitted, **explain exactly why** in the
   handoff, so the next session does not have to reconstruct the reason.

Do not merge and do not release as part of wrapping up. Those are explicit
requests, never housekeeping.

---

## 6. Context maintenance

These are the rules for **what may be written where**. They live here and
nowhere else. [`docs/context.md`](docs/context.md) is navigation only — which
file to read for which task — and must not restate them.

Five invariants:

- **A fact lives in exactly one file.** Do not copy content between them; a
  pointer is enough.
- **The handoff is volatile only.** Current task, progress, blockers,
  verification state, next actions. Anything that outlives the current piece of
  work does not belong there.
- **Branch, commit hashes and working-tree state are never written into a
  tracked file.** Read them from git. This repository is public, and that detail
  is stale within hours of being written.
- **A settled decision goes only in `docs/decisions/`.** If it has no stated
  reopening condition, it is not settled yet. An unverified belief goes only in
  `docs/product-discovery.md`, labelled as such, and never appears elsewhere as
  though it were established.
- **Durable technical knowledge goes in `docs/architecture.md`** — domain
  concepts, structure, and long-lived constraints. If you find yourself writing
  a limitation into the handoff, it probably belongs there instead.

When a rule in this file changes, change it here only.
