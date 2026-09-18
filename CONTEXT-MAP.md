# Context Map

Skillworks holds more than one product area, and each one keeps its own language. A word that loses
in one context is free in another, so the map is what tells a reader, and the check, which glossary
judges a file.

## Contexts

- [Studio](./CONTEXT.md) — the local app that watches, authors, tests and publishes the catalogue
- [Architecture](./src/Skillworks.Architecture/CONTEXT.md) — the check that holds the shape of the code

A context is a product area. A large repository splits its contexts by project; a small one splits by
folder. The test is the same either way.

## Relationships

- **Architecture → Studio**: the check reads Studio's glossary to decide which words a file may use.
  It reads Studio's code as text and never as code.
- **Studio → Architecture**: nothing. Studio does not know the check exists.

## The next context

The catalogue is a third product area, and `Skill` already means two things in this repository: a
folder of instructions a developer writes, and a name in telemetry with Activations and a Cost. The
catalogue gets its own context, and its own glossary, the day Author or Publish writes code of its
own. Until then its words sit in Studio's glossary, because a context with no code gives the check
nothing to judge.

## Paths

Each context owns the paths listed beneath it. A source file is judged by the context that claims it
and by no other. A file no context claims is judged by none of them, and a path two contexts claim is
a breach, so the map cannot drift away from the tree.

```yaml
contexts:
  studio:
    glossary: CONTEXT.md
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
    code:
      - src/Skillworks.Architecture
      - tests/Skillworks.Architecture.Tests
```
