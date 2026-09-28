---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

Save it in `.handoff/` at the repo's top level, which `git rev-parse --show-toplevel` prints. Name the file for today's date and a short slug of its subject, such as `2026-09-28-setup-order.md`, so the folder reads in order. Create `.handoff/` when it is missing.

A handoff must never be committed. When `git check-ignore -q .handoff/` fails at the top level, because git does not ignore the folder or because there is no git repo, save to the temporary directory of the user's OS instead. Then tell the user the full path you saved to.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
