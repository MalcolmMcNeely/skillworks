---
name: domain-modeling
description: Build and sharpen a project's domain model. Use when discussing codebase terminology, writing or editing a CONTEXT.md, or recording or editing an ADR.
---

# Domain Modeling

Actively build and sharpen the project's domain model as you design. This is the *active* discipline — challenging terms, inventing edge-case scenarios, and writing the glossary and decisions down the moment they crystallise. (Merely *reading* `CONTEXT.md` for vocabulary is not this skill — that's a one-line habit any skill can do. This skill is for when you're changing the model, not just consuming it.)

## File structure

Most repos have a single context:

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts. The map points to where each one lives:

```
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                          ← decisions for every context
├── src/
│   ├── ordering/
│   │   └── CONTEXT.md
│   └── billing/
│       └── CONTEXT.md
```

Create files lazily — only when you have something to write. If no `CONTEXT.md` exists, create one when the first term is resolved. The trees show `docs/adr/`, but every new ADR goes to the folder `adr-folder` names in `docs/agents/domain.md`. If that folder does not exist, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `CONTEXT.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Don't batch these up — capture them as they happen. Use the format in [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md).

`CONTEXT.md` should be totally devoid of implementation details. Do not treat `CONTEXT.md` as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).

### Commit each change the moment it settles

More than one person runs agent work against a repo at once, and a conversation can sit open for an hour while the user thinks. A word settled in that hour lives only in this session's context, so a teammate working beside you can reserve the same word for something else, and one of the two designs then has to be reworked.

So commit every change to `CONTEXT.md` or an ADR as soon as it settles, and push it to the Target branch. Never hold them to the end of the session.

- **Find the Target branch.** Read `target-branch` in `docs/agents/loop.json`. A branch name is the Target branch. The word `spec` means the design gets a branch of its own; see [The spec's branch](#the-specs-branch).
- **Stage by path.** Stage only the file you settled. Work in progress elsewhere in the tree is never swept into a glossary commit.
- **Prefix the subject line.** `Glossary:` for a `CONTEXT.md` change, `ADR:` for an ADR, so the log says which kind of change it was without anyone opening it.
- **Pull, then push.** A push onto a branch a teammate has moved is rejected, so pull first and push the rebased commit. Read what the pull brings down: when a teammate's change touches ground this session already settled, say so. What to re-ask is then a question for this session.

### The spec's branch

In `spec` mode the spec is reviewed as one pull request, and its Target branch is `spec/<slug>`. A protected default branch refuses a direct push, so no word or ADR goes there.

With `export` set to `true` in `docs/agents/loop.json`, follow [The spec's branch with the Export](#the-specs-branch-with-the-export) instead of this section.

**The first word or ADR settled** creates the branch. The slug is short, in kebab case, and comes from the design's subject. Cut it from the newest default branch, commit the settled file on it, push it, and open a draft pull request to the default branch:

```bash
default=$(gh api "repos/{owner}/{repo}" --jq .default_branch)
git fetch origin "$default"
git switch -c "spec/<slug>" "origin/$default"
git add <the settled file>
git commit -m "Glossary: <word>"
git push -u origin "spec/<slug>"
gh pr create --draft --base "$default" --head "spec/<slug>" --title "<the design's subject>" --body "The design of <the design's subject>, as the grill settles it."
```

No spec exists yet, so the body names none. `to-spec` adds the closing keyword when it publishes the spec.

**Every later word or ADR** goes to the same branch. Stay on `spec/<slug>`, pull, and push there.

### The spec's branch with the Export

With `export` set to `true` in `docs/agents/loop.json`, the loop later Exports the spec's work onto the branch this session is on when the first word or ADR settles. That branch is the Export branch. The spec's Target branch is `skillworks/spec/<the Export branch>`, cut from the Steering branch, `skillworks/steering`.

**The first word or ADR settled** creates the Target branch. Stay on the Export branch, leave the settled file uncommitted, and run `cut-target-branch`, the one command that cuts it:

```bash
cut-target-branch
```

It rebases the Steering branch onto the commit the Export branch sits on and pushes it to `origin`. Then it cuts the Target branch from the Steering branch, pushes it, and switches to it. The settled file comes with it. Commit the file there, with its prefix, and push. Run no git step of your own to make either branch, so the steps are the same in every run.

Open no pull request, and make no `gh` call to find the default branch. The developer opens the one pull request, from the Export branch, after the loop Exports onto it.

When the command says the Steering branch does not rebase, stop the grill there. It pushed nothing and cut nothing. Name each file it lists to the developer, and say that they mend those files on `skillworks/steering`, push it, and start again on the Export branch.

**Every later word or ADR** goes to the same Target branch. Stay on it, pull, and push there.
