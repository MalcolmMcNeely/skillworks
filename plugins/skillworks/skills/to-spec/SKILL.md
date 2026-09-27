---
name: to-spec
description: Turn the current conversation into a spec and publish it to the project issue tracker — no interview, just synthesis of what you've already discussed.
---

This skill takes the current conversation context and codebase understanding and produces a spec. Do NOT interview the user — just synthesize what you already know.

The issue tracker should have been provided to you. If not, tell the user to run `/skillworks:skillworks-setup`.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching.

2. Sketch out the seams at which you're going to test the feature. Existing seams should be preferred to new ones. Use the highest seam possible. If new seams are needed, propose them at the highest point you can. The fewer seams across the codebase, the better - the ideal number is one. Write them into the spec's Testing Decisions.

3. Read `tracker` and `target-branch` in `docs/agents/loop.json`. A branch name is the Target branch for this spec. The word `spec` means the spec gets a branch of its own; see [The spec's branch](#the-specs-branch) and do its first part now.

4. Commit whatever the conversation changed on disk — `CONTEXT.md`, ADRs, glossary entries — and push it to the Target branch. The spec points at decisions that must already be in the repo, because every session after this one starts with an empty context and can only find them there.

5. Write the spec using the template below. The spec title should begin with "SPEC:". Then publish it:
   - With `github`, publish it to the project issue tracker and apply the `ready-for-agent` label. In `spec` mode, the spec carries the `## Branch` section; with a branch name, leave that section out.
   - With `files`, follow [The files Tracker](#the-files-tracker). The spec never carries the `## Branch` section, because its frontmatter names the branch.

6. In `spec` mode, do the second part of [The spec's branch](#the-specs-branch).

7. Report the spec's number: with `github` its issue number and URL, with `files` its number and folder. That number is the argument to `/skillworks:spec-loop`. In `spec` mode, report the pull request's URL too.

## The files Tracker

With `files`, the spec is a folder in `.specs/`, and `tracker-publish` writes it. The command numbers the spec one above the highest number on the remote, and pushes the folder at once. Two specs written at once get two numbers: the remote refuses the second push, and the command reads again and takes the next number. In `spec` mode each spec pushes to a branch of its own, so the same push also holds the number on the remote as `refs/skillworks/specs/<number>`, and a second spec cannot take it. It writes through an index of its own, so it never touches the checkout.

1. Write the spec to a file outside the repo, such as in `$(mktemp -d)`. Its first line is `# SPEC: <title>`, and the template's sections follow. Leave out the frontmatter, because the command writes it: `status: open`, and in `spec` mode `branch`.
2. Publish it. The slug is short and in kebab case. In `spec` mode, name the spec's branch last, so the folder sits on that branch and the pull request carries the spec and its code together:

   ```bash
   tracker-publish spec <slug> <file>                 # target-branch names a branch
   tracker-publish spec <slug> <file> spec/<slug>     # target-branch says spec
   ```

3. It prints the number, a tab and the folder, such as `8	.specs/0008-local-tracker`. Pull the branch, so the checkout holds the folder too.

## The spec's branch

In `spec` mode the spec is reviewed as one pull request, and its Target branch is `spec/<slug>`. The loop reads the branch from the spec's `## Branch` section with `github`, and from its frontmatter with `files`, so a spec without it stops the loop.

**First part, before the spec is published.** Find the branch.

- If the grill settled a word or an ADR, it already created `spec/<slug>` and a draft pull request. Use that branch. `git branch --show-current` names it when this session is still on it.
- If the grill settled nothing, create the branch. The slug is short, in kebab case, and comes from the design's subject. Cut it from the newest default branch and push it. With `files`, the remote may not be on GitHub, so read the default branch from `git remote show origin`, on its `HEAD branch:` line, and not from `gh`:

  ```bash
  default=$(gh api "repos/{owner}/{repo}" --jq .default_branch)                  # github
  default=$(git remote show origin | sed -n 's/.*HEAD branch: //p')              # files
  git fetch origin "$default"
  git switch -c "spec/<slug>" "origin/$default"
  git push -u origin "spec/<slug>"
  ```

**Second part, after the spec is published and the work pushed.** With `files` there is no issue for the pull request to close, because the loop closes the spec in its folder. Open a draft pull request to the default branch the way the remote's host does, with `gh pr create --draft` and no closing line when the host is GitHub. Skip the rest of this part.

With `github`, the pull request's body names the spec with a closing keyword, so a merge closes the spec. Ticket commits never carry one, so this body is the only thing that closes the spec.

- If no pull request exists for the branch, open a draft one to the default branch:

  ```bash
  gh pr create --draft --base "$default" --head "spec/<slug>" --title "<the spec's title, without SPEC:>" --body "Closes #<spec>"
  ```

  A branch with no commit beyond the default branch cannot open a pull request. Push an empty commit that names the spec first: `git commit --allow-empty -m "Open the pull request for spec #<spec>"`.

- If the grill already opened one, add the closing keyword to its body. Read the body, and write it back with `Closes #<spec>` on a line of its own at the end:

  ```bash
  gh pr view "spec/<slug>" --json number,body
  gh api -X PATCH "repos/{owner}/{repo}/pulls/<number>" -f body="<the body, then Closes #<spec>>"
  ```

<spec-template>

## Branch

`spec/<slug>`, in `spec` mode only. The branch name alone, on the first line under the heading.

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature.

</spec-template>
