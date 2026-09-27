# Surfaces

A Surface is one place a change can have to reach besides the code that does the work. The grill
asks about each Surface a change touches, once the design is settled, and the spec carries each
answer to the tickets that build it.

Each `##` section below is one Surface, with three parts:

- **Where it lives:** the file or folder that holds it.
- **The question:** the one question the grill asks about it.
- **What to capture:** what the answer has to hold, so the builder can bring the Surface into step.

Add a section for each place your team keeps in step with the code. Delete a Surface your repo does
not have, so the grill does not ask about it. A file with no Surface in it skips the step.

A Surface you add reads like this one:

```markdown
## The changelog

- **Where it lives:** `CHANGELOG.md`
- **The question:** Does a user who upgrades see a difference, and which entry tells them?
- **What to capture:** The version the entry goes under, and the difference it names: a change a
  user can see, a setting renamed or removed, or a default that moved.
```

## The README

- **Where it lives:** `README.md`
- **The question:** Does this change alter what a newcomer reads first: what the project is, how to
  install it, or how to start?
- **What to capture:** The section of the README that changes, and what it has to say once the
  change Lands. Point at the section, and do not copy it.

## The user docs

- **Where it lives:** `docs/`
- **The question:** Which page does a user read to learn what this change adds or alters?
- **What to capture:** Each page that changes, and what it has to say once the change Lands. Name a
  page the change needs that does not exist yet. Point at each page, and do not copy it.
