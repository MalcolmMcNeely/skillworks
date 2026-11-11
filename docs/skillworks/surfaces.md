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

## The README

- **Where it lives:** `README.md`
- **The question:** Does this change rename, move or add something the README names: a command, a
  path, a setup or run step, or a doc the README links to?
- **What to capture:** The exact line that changes, and what it says after. A change may alter a
  line, or add one new item to the setup or run steps. It never adds a sentence, a paragraph or a
  section.

Keep the heading `## The README` as it is, so that the loop can find this Surface.

## The user docs

- **Where it lives:** `docs/usage/`
- **The question:** Which page does a team that uses the Plugin read to learn what this change adds
  or alters: setup, the loop, Steering or the Suite?
- **What to capture:** Each page that changes, and what it has to say once the change Lands. Name a
  page the change needs that does not exist yet. Point at each page, and do not copy it.

## The Seeds

- **Where it lives:** `plugins/skillworks/skills/skillworks-setup/seeds/`
- **The question:** Does this change add a Steering file, or change what a Seed says, so that every
  team gets it the next time setup runs?
- **What to capture:** Each Seed that is added or changed, in general words with no word from this
  repo, and whether this repo's own copy changes with it. For a new Steering file, capture that every
  team's loop stops at its preflight until the team runs setup again.
