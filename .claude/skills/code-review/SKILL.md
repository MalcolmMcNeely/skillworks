---
name: code-review
description: Review the changes since a fixed point (commit, branch, tag, or merge-base) along three axes — Standards (does the code follow this repo's documented coding standards?), Spec (does the code match what the originating issue/spec asked for?) and Architecture (is it in the right module, pointing the right way?). Runs the reviews in parallel sub-agents and reports them side by side. Use when the user wants to review a branch, a PR, work-in-progress changes, or asks to "review since X".
---

Three-axis review of the diff between `HEAD` and a fixed point the user supplies:

- **Standards** — does the code conform to this repo's documented coding standards?
- **Spec** — does the code faithfully implement the originating issue / spec?
- **Architecture** — is the code in the right module, and do its dependencies point the way this repo says they should?

Each axis runs as a **parallel sub-agent** so they don't pollute each other's context, then this skill aggregates their findings.

The issue tracker should have been provided to you. If `docs/agents/issue-tracker.md` is missing, tell the user to run `/skillworks-setup`.

## Process

### 1. Pin the fixed point

Whatever the user said is the fixed point — a commit SHA, branch name, tag, `main`, `HEAD~5`, etc. If they didn't specify one, ask for it, unless the review is of an uncommitted change.

**An uncommitted change** has no commits for a three-dot diff to see, and needs no fixed point. Run `git add -N .` so new files show, then use `git diff HEAD` and `git diff HEAD --stat -M` in place of the commands below. There is no commit list.

Capture the diff command once: `git diff <fixed-point>...HEAD` (three-dot, so the comparison is against the merge-base). Also note the list of commits via `git log <fixed-point>..HEAD --oneline`.

Before going further, confirm the fixed point resolves (`git rev-parse <fixed-point>`) and the diff is non-empty. A bad ref or empty diff should fail here — not inside three parallel sub-agents.

Also capture `git diff <fixed-point>...HEAD --stat -M`, which the Architecture axis needs: `-M` is what turns a rename into a rename rather than a delete plus an add.

### 2. Identify the spec source

Look for the originating spec, in this order:

1. Issue references in the commit messages (`#123`, `Closes #45`, GitLab `!67`, etc.) — fetch via the workflow in `docs/agents/issue-tracker.md`.
2. An issue number or a path the user passed as an argument.
3. A spec file under `docs/`, `specs/`, or `.scratch/` matching the branch name or feature.
4. If nothing is found, ask the user where the spec is. If they say there isn't one, the **Spec** sub-agent will skip and report "no spec available".

### 3. Identify the standards sources

Anything in the repo that documents how code should be written, such as `CODING_STANDARDS.md` or `CONTRIBUTING.md`.

Always include the Claude rules files: every file in `.claude/rules/`. Claude wrote the code under those rules, so the review holds it to the same ones.

On top of whatever the repo documents, the Standards axis always carries the **smell baseline** below — a fixed set of Fowler code smells (_Refactoring_, ch.3) that applies even when a repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented repo standard always wins; where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic ("possible Feature Envy"), never a hard violation — and, like any standard here, skip anything tooling already enforces.

Each smell reads *what it is* → *how to fix*; match it against the diff:

- **Mysterious Name** — a function, variable, or type whose name doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky.
- **Duplicated Code** — the same logic shape appears in more than one hunk or file in the change. → extract the shared shape, call it from both.
- **Feature Envy** — a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps** — the same few fields or params keep travelling together (a type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession** — a primitive or string standing in for a domain concept that deserves its own type. → give the concept its own small type.
- **Repeated Switches** — the same `switch`/`if`-cascade on the same type recurs across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery** — one logical change forces scattered edits across many files in the diff. → gather what changes together into one module.
- **Divergent Change** — one file or module is edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality** — abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains** — long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man** — a class or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest** — a subclass or implementer that ignores or overrides most of what it inherits. → drop the inheritance, use composition.

Those judge code. A test carries them and four of its own, under one question: **what change to the code would make this test fail?** A test with no answer is a finding however tidy it reads, because a suite that can't go red buys nothing and gets read as proof.

- **Tautological Assertion** — the expected side is worked out the way the code works it out, so both sides move together and no defect can show. → write the expected value out by hand.
- **Untriggered Fixture** — the input holds nothing the behaviour under test acts on, so the assertion would still hold with that behaviour deleted. → put the trigger in the fixture, and settle it by deleting the behaviour and watching the test go red.
- **Unguarded Enumeration** — a test walks files, rows, or elements and judges what it found without proving it found any, so an empty walk passes. → pin the count the walk is expected to reach.
- **Stub Echo** — a stub is handed a value and the assertion only checks that value came back, so it measures the stub. → assert on what the code made of the value, not on the value.

### 4. Identify the architecture sources

Three kinds, and each outranks the one before it.

**Documented** — anything in the repo that says how the code is *arranged*, as opposed to how it is written: `ARCHITECTURE.md`, `CONTEXT.md`, a `docs/adr/` or `decisions/` folder, a README section on layout. Decisions are often recorded somewhere a template wouldn't predict — if the repo has a doc telling agents where its decisions live, read that first and follow it.

**Written as rules** — the placement rules in `.claude/rules/`, and the context map beside them. Step 3 hands the whole of `.claude/rules/` to Standards, but the half that says *where a file goes, and which folder may read which*, is an arrangement rule rather than a style one, and this axis is the one that judges by it. Read the context map too: a rule reaches only the code the map gives it, and a path two contexts claim breaches `contexts`.

In this repo that file is `.claude/rules/file-placement.md`, and its eight Slice rules are the ones the agent wrote the code under. Read them there, and judge placement and direction against what they say. Cite a breach by the name of the check that catches it:

| Check | The rule it runs |
|---|---|
| `slice-folders` | 1, a Slice comes first |
| `concern-folders` | 2, a Concern comes beneath, in the front end |
| `slices-stay-apart` | 3, a Slice never reads another Slice |
| `shared-stays-below` | 4, `Shared` never reads a Slice |
| `shared-names-a-word` | 5, `Shared` has one door |
| `slice-names-match` | 6, a Slice keeps its name everywhere |

Rules 7 and 8 have no check behind them, and nor does the exemption that lets a test read a Slice. The front end is held by `src/Skillworks.Studio.Web/.dependency-cruiser.cjs`, which names its own breaches, so quote whichever name the run printed. The table is an index from a breach back to a rule, and the rules themselves stay in the one file.

Holding the author and the reviewer to one document is the point of this axis, so two baseline items bend wherever the repo has written the rule down:

- **A shared folder with a written door is not grab-bag growth.** The baseline item is about a folder nobody decided on. Judge against the door the repo wrote, not against the name.
- **Duplication across a boundary can be correct.** Where the repo says two modules may hold one name, the merge is the defect, not the duplication.

**Executable** — a boundary rule the repo can actually run. This is the highest-trust source, because it is enforced rather than aspired to:

| Look for | Ecosystem |
|---|---|
| `.dependency-cruiser.*`, `eslint-plugin-boundaries`, `import/no-restricted-paths`, Nx `tags` | JS / TS |
| An architecture test project, the `ProjectReference` graph across `*.csproj`, `.editorconfig` layering rules | .NET |
| `importlinter` / `.importlinter`, `tach.toml` | Python |
| `internal/` directories, `go.mod` boundaries | Go |
| `module-info.java`, ArchUnit tests, Maven module graph | Java |

**If an executable rule exists, run it rather than reason about it** — `npm run lint`, `depcruise`, `lint-imports`, `dotnet test`, `dotnet build`, whatever the repo wires it to. A violation it reports is a fact, not a judgement call, and belongs at the top of the axis. Say in the report which command you ran; if none exists, say that too, because "this repo cannot check its own boundaries" is itself the finding a reader wants.

Where a check of the repo's own reads the rules files, the last two kinds are one thing: the file is the text and the check is the run. Here `dotnet test Skillworks.slnx` runs `Skillworks.Architecture` over the whole tree, and `npm run lint` in `src/Skillworks.Studio.Web` runs dependency-cruiser over the front end. Each names the rule, the path and what to do about it, so quote a breach as it came.

On top of whatever the repo has, the Architecture axis always carries the **arrangement baseline** in [`ARCHITECTURE-BASELINE.md`](ARCHITECTURE-BASELINE.md) — nine failures of placement and direction that apply even when a repo documents nothing, in the same *what it is* → *how to fix* shape as the smell baseline. It sits in its own file because only the sub-agent needs it; pass the path, don't paste the contents.

Three rules bind the axis, and the third is the one that decides whether anyone keeps reading its reports:

- **The repo overrides.** A documented rule or a recorded decision wins. Don't re-litigate an ADR — if the diff contradicts one, that is the finding; if the *ADR* looks wrong, say so once and move on.
- **Diff-introduced only.** Standing debt is not a finding. Report what this change introduced, or made materially worse. An axis that re-reports the same architecture every run gets skimmed and then skipped.
- **Cite or drop it.** Every finding names either the doc/rule it breaches or the baseline item, and quotes the line — usually a single import. Architecture judgement without evidence is just taste, and it is the failure this axis is most prone to.

**Skip the axis** when the diff sits inside one module and touches no config, no dependency manifest, no new file and no file move — there is no arrangement question to answer. A new file asks which folder it belongs in and a moved file asks which way it now points, so neither of those skips. Note the skip in the report.

### 5. Spawn the sub-agents in parallel

**Standards sub-agent prompt** — include:

- The full diff command and commit list.
- The list of standards-source files you found in step 3, **plus the smell baseline from step 3** pasted in full — the sub-agent has no other access to it.
- The brief: "Report — per file/hunk where relevant — (a) every place the diff violates a documented standard: cite the standard (file + the rule); and (b) any baseline smell you spot: name it and quote the hunk. Distinguish hard violations from judgement calls — documented-standard breaches can be hard, but baseline smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything tooling enforces. Under 400 words."

**Spec sub-agent prompt** — include:

- The diff command and commit list.
- The path or fetched contents of the spec.
- The brief: "Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words."

If the spec is missing, skip the Spec sub-agent and note this in the final report.

**Architecture sub-agent prompt** — include:

- The diff command, the `--stat -M` command, and the commit list.
- The architecture sources from step 4: the documented files by path, the placement rules file and the context map by path, every executable check and the exact command that runs it, and the path to `ARCHITECTURE-BASELINE.md` — the sub-agent reads that itself.
- The three binding rules from step 4, verbatim, and the two baseline bends beneath them.
- The brief: "First run every boundary check the repo has, and report what each one says. Then read the placement rules file, because it is the document the code was written under, and the context map, because it says which code those rules reach. Then, for **every module the diff touches**: (a) does anything the diff added point the wrong way, cross a seam it shouldn't, or reach past a module's public entry point; (b) is every added or moved file in the module its dependencies say it belongs to, and in the Slice whose job it serves; (c) does the change introduce a cycle; (d) does any folder the diff creates breach a written placement rule. Cite the written rule by its name, or name the baseline item, for every finding, and quote the import or path it turns on. A finding with neither a rule nor a baseline item behind it is taste, so drop it. Report only what this diff introduced or worsened — standing debt is out of scope. Under 400 words."

Unlike Standards, this axis needs to read outside the diff: an import line is only wrong relative to the module graph around it. Say so in the prompt, and let it read the tree.

### 6. Aggregate

Present the reports under `## Standards`, `## Spec` and `## Architecture` headings, verbatim or lightly cleaned. Do **not** merge or rerank findings — the axes are deliberately separate (see _Why three axes_).

End with a one-line summary: total findings per axis, and the worst issue _within each axis_ (if any). Don't pick a single winner across axes — that's the reranking the separation exists to prevent.

## Why three axes

A change can pass on one axis and fail on another, so each masks the others when merged:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions → **Spec pass, Standards fail.**
- Code that is well named, well tested, and exactly what the issue asked for, in a module that should never have imported it → **Standards and Spec pass, Architecture fail.**

The third axis is separate from Standards for two further reasons. Its evidence is different — Standards reads the diff, Architecture needs the module graph the diff sits in. And its remedies cost differently: "rename this" and "invert this dependency" do not belong in one ranked list, because the cheap findings crowd out the expensive ones.
