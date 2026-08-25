# 0006 — Turkish is the default interface language

## Decision

Turkish is the default and the fallback interface language. English is an
explicit choice. **Only the interface is translated**: a draft, a headline, a
repeated paragraph and a publisher's name are reproduced exactly as given.

## Why

This is a tool for TRT's editors. Arriving in English until asked otherwise
would treat their language as the exception.

Content is not translated because the report quotes evidence. Translating a
repeated paragraph would mean the editor is shown something the page does not
contain.

## Evidence and context

- **Rejected — an English-first interface with Turkish as an option.**
- Negotiation order: `X-Aether-Language` → `Accept-Language` → Turkish. A manual
  switcher persists to `localStorage` and beats the browser preference.
- Wording tables are per-language and live in presentation only, which is what
  makes a second language a table rather than a rewrite
  ([0007](0007-separate-finding-codes-from-wording.md)).

## Consequences

Every new finding needs a wording entry per supported language before it ships.

## Implementation status

Settled as a decision; not yet released as code. Progress is tracked in
[`../handoff.md`](../handoff.md) — a decision record does not carry status.

## Reopen when

The product's primary audience changes.
