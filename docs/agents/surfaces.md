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
## The sample app

- **Where it lives:** `samples/`
- **The question:** Does a visitor who clones the repo need to see this change used in the sample
  app?
- **What to capture:** Which sample project changes, and what it shows once the change Lands: a new
  example, or a change to one already there.
```

## The user docs

- **Where it lives:** `docs/usage/`
- **The question:** Which page does a team that uses the Plugin read to learn what this change adds
  or alters: setup, the loop, Steering or the Suite?
- **What to capture:** Each page that changes, and what it has to say once the change Lands. Name a
  page the change needs that does not exist yet. Point at each page, and do not copy it.
