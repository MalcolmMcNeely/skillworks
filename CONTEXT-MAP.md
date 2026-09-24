# Context Map

Skillworks holds more than one product area, and each one keeps its own language. A word that loses
in one context is free in another, so the map is what tells a reader, and the check, which glossary
judges a file.

## Contexts

- [Studio](./CONTEXT.md) — the local app that watches, authors, tests and publishes the Plugin
- [Architecture](./src/Skillworks.Architecture/CONTEXT.md) — the check that holds the shape of the code
- [Loop](./.claude/CONTEXT.md) — the setup an agent runs under, and the scripts that drive it

A context is a product area. A large repository splits its contexts by project; a small one splits by
folder. The test is the same either way.

## Relationships

- **Architecture → Studio**: the check reads Studio's glossary to decide which words a file may use.
  It reads Studio's code as text and never as code.
- **Studio → Architecture**: nothing. Studio does not know the check exists.
- **Architecture → Loop**: the check reads Loop's glossary to decide which words its scripts may use,
  and judges the scripts the same way it judges the rest.
- **Loop → Studio**: the scripts run Studio's build and its tests. They never read Studio's code.

## The next context

The Plugin is another product area, and `Skill` already means two things in this repository: a
folder of instructions a developer writes, and a name in telemetry with Activations and a Cost. The
Plugin gets its own context, and its own glossary, the day Author or Publish writes code of its
own. Until then its words sit in Studio's glossary, because a context with no code gives the check
nothing to judge.

## Paths

Each context owns the paths listed beneath it. A source file is judged by the context that claims it
and by no other. A file no context claims is judged by none of them, and a path two contexts claim is
a breach, so the map cannot drift away from the tree.

`slices` says whether a context lays its code out in Slices, and the Slice rules judge the code of a
context that declares them and no other code. Studio declares them: a folder at the top of one of its
code roots is a job Studio does, or `Shared`. Architecture does not: its top folders are named for
the rules it holds the code to, and a rule is not a job an app does. A context laid out that way is
left to its own shape rather than measured against one it was never built to.

```yaml
contexts:
  studio:
    glossary: CONTEXT.md
    slices: true
    code:
      - src/Skillworks.AppHost
      - src/Skillworks.Core
      - src/Skillworks.ServiceDefaults
      - src/Skillworks.Studio.Api
      - src/Skillworks.Studio.Web
      - tests/Skillworks.Core.Tests
      - tests/Skillworks.Studio.Api.Tests
  architecture:
    glossary: src/Skillworks.Architecture/CONTEXT.md
    slices: false
    code:
      - src/Skillworks.Architecture
      - tests/Skillworks.Architecture.Tests
  loop:
    glossary: .claude/CONTEXT.md
    slices: false
    code:
      - .claude
      - plugins/skillworks
      - scripts
      - tests/plugins/skillworks/scripts
```
