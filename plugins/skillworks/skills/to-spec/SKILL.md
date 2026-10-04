---
name: to-spec
description: >
  Turn the current conversation into a spec and publish it to the project issue tracker — no
  interview, just synthesis of what you've already discussed. Not for turning a plain talk into a
  spec: the developer starts the Dev loop with /skillworks:grill, which runs this skill at its end.
---

This skill takes the current conversation context and codebase understanding and produces a spec. Do not interview the user — just synthesize what you already know.

The issue tracker should have been provided to you. If not, tell the user to run `/skillworks:skillworks-setup`.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching.

2. Sketch out the seams at which you're going to test the feature. Pick them by the team's testing rule, `docs/agents/rules/testing.md`, which says how high and how few they are. Write them into the spec's Testing Decisions.

3. Read `tracker` and `target-branch` in `docs/agents/loop.json`. A branch name is the Target branch for this spec. The word `spec` means the spec gets a branch of its own; see [The spec's branch](#the-specs-branch) and do its first part now.

4. Commit whatever the conversation changed on disk — `CONTEXT.md`, ADRs, glossary entries — and push it to the Target branch. The spec points at decisions that must already be in the repo, because every session after this one starts with an empty context and can only find them there.

5. Write the spec using the template below. The spec title should begin with "SPEC:". Keep the three counted sections in the shape [The counted shape](#the-counted-shape) gives. Then publish it as [Publishing the spec](#publishing-the-spec) says.

6. In `spec` mode, do the second part of [The spec's branch](#the-specs-branch).

7. Report the spec's number, and what `tracker-publish` printed beside it: with `github` its URL, with `files` its folder. That number is the argument to `/skillworks:spec-loop`. In `spec` mode, report the pull request's URL too.

## The counted shape

The spec loop counts the drift check's Verdicts against the spec, so it reads three sections in a fixed shape:

- **User Stories** is a numbered list that starts at 1 and skips and repeats no number. Each story is `S<n>`.
- **Implementation Decisions** is a numbered list in the same way. Each decision is `D<n>`.
- **Surfaces** holds one list item per Surface, and each item opens with the Surface's name in bold. The name is the item. A spec that touches no Surface says "None" under the heading and nothing else.

An item runs over several lines when its later lines are indented, so a nested list stays part of its item. Testing Decisions are not counted. The loop reads the shape before its first ticket, and turns down a spec in another shape.

## Publishing the spec

`tracker-publish` writes the spec with either Tracker, from one file and one command.

1. Write the spec with the Write tool to `.spec-loop/drafts/<slug>.md` in this checkout. The slug is short and in kebab case. Its first line is `# SPEC: <title>`, and the template's sections follow. Leave out the `## Branch` section and any frontmatter, because the command writes them. Git ignores `.spec-loop/`, so the file leaves the checkout clean. Write nowhere outside the checkout, and make no temp folder, so no skill that publishes asks for a permission the loop cannot give.
2. Publish it. In `spec` mode, name the spec's branch last:

   ```bash
   tracker-publish spec <slug> .spec-loop/drafts/<slug>.md                 # target-branch names a branch
   tracker-publish spec <slug> .spec-loop/drafts/<slug>.md spec/<slug>     # target-branch says spec
   ```

3. It prints the number, a tab, and then the issue's URL with `github` or the folder with `files`, such as `8	.specs/0008-local-tracker`. With `files`, pull the branch, so the checkout holds the folder too.

When the command fails, run it again. It files nothing twice.

### With `github`

The command files one issue. Its title is the `# SPEC: ` heading, its body is the text below that heading, and it carries the `ready-for-agent` label. In `spec` mode it writes the `## Branch` section at the top of the body, from the branch named. Above all of it, the body opens with a hidden line that holds a hash of the title and the body. The command first looks for an open `ready-for-agent` issue whose body opens with the same hidden line. When it finds one, it files nothing and prints that issue's number and URL, so a run after a network failure never files a second spec. A spec with the same title as an open spec and a different body gets an issue of its own, and the command names each open spec with that title. The command writes a note on stderr when it finds the spec already filed, and when another open spec shares the title. Tell the developer each note it writes.

### With `files`

The spec is a folder in `.specs/`. The command writes its frontmatter: `status: open`, and in `spec` mode `branch`, so the folder sits on that branch and the pull request carries the spec and its code together. The command numbers the spec one above the highest number on the remote, and pushes the folder at once. Two specs written at once get two numbers: the remote refuses the second push, and the command reads again and takes the next number. In `spec` mode each spec pushes to a branch of its own, so the same push also holds the number on the remote as `refs/skillworks/specs/<number>`, and a second spec cannot take it. It writes through an index of its own, so it never touches the checkout.

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

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories, from 1 with no number skipped or repeated. Each user story should be in the format `As an <actor>, I want a <feature>, so that <benefit>`.

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
2. As a mobile bank customer, I want to see which account a payment left, so that I can match it to my statement
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A numbered list of the implementation decisions that were made, from 1 with no number skipped or repeated. A decision can cover:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do not include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits. Indent the snippet under its decision, so it stays part of that item.

<decision-example>
1. The balance is read through the accounts module, and never straight from its tables.
2. A balance older than a minute is shown with the time it was read.
</decision-example>

## Surfaces

For each Surface in `docs/agents/surfaces.md` the change touches, one list item that opens with the Surface's name in bold, then its path, then the requirement the grill captured: what the Surface has to say once the change Lands. Point at the Surface by its path, and do not copy its content. Leave out a Surface the change does not touch. With no Surface touched, or no Surfaces file, write "None" and nothing else.

<surface-example>
- **The user docs** (`docs/usage/`): the accounts page says how old a balance can be before it is marked.
</surface-example>

When `docs/agents/surfaces.md` holds a Surface headed `## The README`, outside a code fence, name the README here and nowhere else in the spec: never in a user story, an implementation decision or a testing decision. Its item is the only route by which the loop changes the README, so a README named anywhere else becomes an edit nobody asked for. With no README Surface, the README is any other file.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

When the grill found that the change deserves README text the README Surface's limit does not allow, list it here as "the README: a focused session". Nothing builds it, and no issue is filed for it.

## Further Notes

Any further notes about the feature.

</spec-template>
