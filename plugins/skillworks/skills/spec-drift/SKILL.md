---
name: spec-drift
description: Compare the work a spec loop produced against what the spec asked for, and report the gaps as a comment on the spec.
disable-model-invocation: true
---

# Spec Drift

The last step of `/skillworks:spec-loop`. Every ticket passed its own acceptance criteria. Nothing so far has asked whether the pile of them is what the spec wanted.

Two arguments: the spec's issue number, then the commit the loop started from.

`/skillworks:spec-drift 42 a1b2c3d`

This repo commits straight to `main`, so there is no branch to diff. The base commit is the only thing that says where the work began. The loop stores it in `.spec-loop/<spec>/base.sha` and passes it in. If it was not passed, read that file. If that is missing too, stop and ask — do not guess a base.

## Process

1. Read the spec issue in full, then every one of its sub-issues with their closing comments.

2. Get the accumulated diff:

   ```bash
   git diff <base>..HEAD
   git log --oneline <base>..HEAD
   ```

3. Classify every user story and implementation decision in the spec as one of:

   - **Done** — the diff delivers it
   - **Partial** — started, not finished
   - **Missing** — no code for it
   - **Contradicts** — the code does something the spec ruled out

   Then list **Unrequested** — behaviour in the diff that no story and no ticket asked for.

   Judge against the **spec**, not against the tickets. A ticket that drifted still passed its own criteria, which is exactly why this step exists.

4. Look for the failure no per-ticket check can see: two tickets that introduced competing names or competing abstractions for one concept. The project glossary is the arbiter.

5. Post the report as a comment on the spec issue.

6. **Report only. Fix nothing.** A fix is new work and needs its own ticket. Do not close the spec either — the human closes it once they have read this report.
