# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

The YAML block at the end holds `adr-folder`: the one folder every new ADR goes to, whatever context it is about, as a path from the repo root. `/skillworks:skillworks-setup` writes it, and preflight stops while it is missing or empty.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists — it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **The folder `adr-folder` names** — read ADRs that touch the area you're about to work in. A team that keeps older decisions in other folders too names them here, so a reader reads those as well.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/skillworks:domain-modeling` skill (reached via `/skillworks:grill` and `/skillworks:improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved. A repo built before it had these files fills them once with `/skillworks:context-backfill`, and setup names it as the next step.

## File structure

Single-context repo (most repos):

```
/
├── CONTEXT.md
├── docs/adr/                          ← adr-folder
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

Multi-context repo (presence of `CONTEXT-MAP.md` at the root):

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← adr-folder, for every context
└── src/
    ├── ordering/
    │   └── CONTEXT.md
    └── billing/
        └── CONTEXT.md
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/skillworks:domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_

```yaml
adr-folder: docs/adr
```
