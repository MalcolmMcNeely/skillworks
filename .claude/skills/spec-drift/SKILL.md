---
name: spec-drift
description: Compare the finished work on a spec branch against what the spec asked for, and report the gaps as a comment on the spec.
disable-model-invocation: true
---

# Spec Drift

The last step of `/spec-loop`. Every ticket passed its own acceptance criteria. Nothing so far has asked whether the pile of them is what the spec wanted.

The argument is the spec's issue number.

## Process

1. Read the spec issue in full, then every one of its sub-issues with their closing comments.

2. Get the accumulated diff:

   ```bash
   git diff "$(git merge-base HEAD main)"..HEAD
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

6. **Report only. Fix nothing.** A fix is new work and needs its own ticket. Do not close the spec either — the human closes it when the PR merges.
