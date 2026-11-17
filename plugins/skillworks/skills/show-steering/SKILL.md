---
name: show-steering
argument-hint: "[<step>] [--path <file>]"
description: Show the Steering a step of the Dev loop reads, and the place each part comes from.
disable-model-invocation: true
---

# Show Steering

Run this command from the repo, with the arguments as the developer typed them:

```bash
show-steering $ARGUMENTS
```

Show what it prints, word for word, in a fenced block. Add nothing to it, and leave nothing out.

With no step, it lists the steps of the Dev loop. A name that is not a step gets the same list, after a line that says so.
