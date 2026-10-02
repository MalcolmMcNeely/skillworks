---
name: skillsmith
description: "Rules for writing a document an agent reads. Use when creating or editing a skill, a CLAUDE.md or AGENTS.md, a rule file, a subagent brief, or a prompt a script sends. Not for prose a person reads: that is unslop."
---

Reference for writing any document an agent reads: a skill, a `CLAUDE.md` or `AGENTS.md`, a rule file, a subagent brief, a prompt a script sends. It is rules to check a draft against, and not steps to run. You are done when the document has been held against every section here that bears on it, and each change you made names the fault it mends.

Three files beside this one hold what only some documents need. Before you draft, read each file whose case applies, and no other:

- `${CLAUDE_SKILL_DIR}/SKILL-MECHANICS.md`, when the document is a skill, or a command file under `.claude/commands/`. It holds how Claude Code starts and loads a skill, arguments, front matter, paths, the commands a skill names, text a program matches, calls between skills, and how to check a skill.
- `${CLAUDE_SKILL_DIR}/SUBAGENT-BRIEFS.md`, when the document is a subagent brief or a subagent definition, or tells the reader to start a subagent.
- `${CLAUDE_SKILL_DIR}/HEADLESS-SESSIONS.md`, when the document will run in a Session that a script starts with `claude -p`, where nobody is there to answer: a skill that is a step of a loop, or the prompt the script sends. The test is where the document runs, and not where you write it.

## The reader

Four facts about the reader shape every rule below.

- **It follows the text to the letter.** A current model reads closely and literally. A line that is stale, untrue, or wider than its author meant is acted on as written, so it does more harm than a line that is only wasted.
- **It does what is asked, and sometimes more.** So a document says where the work stops and what to leave alone.
- **A sentence is a request.** Nothing makes the reader follow it. What must hold every time needs a check outside the model.
- **It already knows a great deal.** What it lacks is what only the author knows: the audience, the environment, the quality bar, the hard calls, and the reason behind each constraint. That is context, and context is never padding.

A line marked **guess** is a working idea that nobody has measured. Nobody knows how often a model follows a document, so promise no rate.

## Changing a document that exists

A change of wording is a hypothesis about what the reader will do. So mend only a fault you can name, and say how to see that the mend worked.

A fault is one of these. The text disagrees with how Claude Code works, with how the model that reads it behaves, with another text loaded beside it, or with what the code and the repo really do. A step has no done test, no exit or no fence. Or a run showed the failure. "This could read better" is not a fault. A document that works gets few changes, and "leave it alone" is a valid result:

- Leave a description that triggers. A reword can stop it triggering, and nothing shows a gain.
- Never cut by length. The harm is in a specific wrong line, and not in volume.
- Add no ban against a failure nobody has seen. It can pull the reader toward that failure.
- Leave style alone: dashes, bold, heading case. Nothing ties them to behaviour, and an untouched line keeps the diff to the changes that have a reason.

Change what the request names. List any other line you would change, with its reason, and leave it in place. Where a line has two fair readings, or a change would shift what the document does, the decision is the owner's: state both readings and the one you would take.

Before the change, in this order:

1. Find what starts the document and what reads its output: a person, Claude, another skill, a script. A script or a test may match its exact text. The repo's `CLAUDE.md` or contributing guide may say where. Search the scripts and the tests for each heading, flag, command name, marker and report shape you mean to touch, and keep the ones that are matched.
2. Find the texts that load beside it or share its sentences: a reference file, a skill that calls it, a twin, the user page that describes it. Change them together, or change none.
3. Read the evidence that already exists before you pay for a run: transcripts, logs, eval traces. Where a run is cheap, run the document as it is first. If it already does the right thing, the new line is a no-op, so leave it out.

With each change, give its check: what to run or read, and what result would show that the change did nothing. A removal is a hypothesis too. If a cut makes things worse, put the line back in its shortest form.

## Where text sits

A **context pointer** is a line in the agent's context that names material outside it and says when to reach for it. A skill's description is one. A line in `CLAUDE.md` that names a doc is another. The agent chooses from the pointer and never from the target, so the pointer's wording decides when the material is reached. Say what the material is, and name each **branch** that should reach it: a branch is a distinct case the document handles. Put the key use first, in words a request would contain. Name kinds of intent, one trigger for each branch. Synonyms are one branch written twice.

Every document spends one of two budgets. **Context load** is the cost of always-loaded text on the agent's window: a `CLAUDE.md` line, an imported rule, a skill description. It is paid on every turn, used or not. **Cognitive load** is the cost on the person, who has to remember which documents exist and when to type each. Spend that where human judgement matters.

Each piece of a document sits on one rung of the **information hierarchy**:

1. **In-file step.** What the agent does, in order.
2. **In-file reference.** Rules and facts consulted on demand. A flat set of peers, such as every rule of a review, is a fine shape.
3. **Disclosed reference.** A separate file behind a pointer, read when the pointer's condition is met.

**Progressive disclosure** is the move down the ladder, out of the file and behind a pointer, so that the top stays legible. The branch is its test. What every branch needs goes in the file, because reaching a pointer is the agent's choice. What only some branches need goes behind a pointer that says when to read it: "Read `X.md` when the API returns an error", and not "see `X.md`". A gotcha stays in the file, because the agent may never meet the cue to open another file for it. When pointed-at material is not reached, check the path and the permission before the wording.

**Co-location** decides what sits beside a piece. Keep a concept's definition, rules, exceptions and reasons under one heading, so reading one part brings the rest. Put a fact where the reader is when it needs it: a fact that step 1 needs does not wait in step 2.

Put first what must survive. Length alone is not a fault. The limits that are real: an always-loaded file is paid for in every Session and every subagent, so keep each `CLAUDE.md` under 200 lines. A skill has a listing budget and a compaction cap, both in `SKILL-MECHANICS.md`.

**Guess:** steps still in view pull the agent to finish the step in front of it early, and a split across a real context boundary (a hand-off or a subagent, never an inline call) removes the pull. Sharpen the done test first. Split only when you have seen the rush.

## What an instruction needs

**The specific thing.** The reader follows a specific instruction and drifts on a general one. Name the file, the command, the tool, the case. "The config should have been provided to you" names nothing the reader can look at, and "Read `config/deploy.json`" does. A number needs both ends: "3+" has no upper bound. Name the allowed case beside the banned one.

**A reader who can act on it.** The first lines of a body say what the reader produces. A body that opens with a line to the person leaves the reader with a map and no task. Keep "you" to one party. Make each condition one the reader can observe: it cannot know that "the user is away".

**The reason, beside it.** Put the "because" in the same sentence or the next. The reason lets the reader apply the rule where it fits and nowhere else. Prose carries a reason, and a bare bullet drops it. Give only a reason you know to be true.

**A done test.** Say how the reader knows the step is done, in a form it can check: "the command printed the URL", "each acceptance criterion has a passing test". "When done" cannot be checked. A **completion criterion** has clarity, which is whether done can be told from not done, and **demand**, which is how much it asks for: "every modified model is accounted for" forces more work than "produce a change list". Demand binds reference too: "every rule applied".

**An exit.** Say what to do when the step cannot be done. The reader tries to get round a step that is impossible, and more so when asking is ruled out. The shape that works is: stop, say what is missing, say what supplies it, and say that nothing was done. Each of these needs its exit:

- A file, a tool or a setting that is not there.
- A command that refuses or fails. Mend what the refusal names and run it again once, then stop and quote it. "Run it again" with no bound is followed with no bound.
- A fact the reader does not have. Say that it is missing. Never leave making one up as the only way to obey.
- A person who answers no, or yes with a change in it.
- The empty case: nothing to review, no ticket left, no step that only this skill can do.

**A wait, or none.** A message with no tool call ends the turn. So "show the list, then test" holds only if both happen in one turn, and "ask the user" ends the turn there. Say which is meant: "state your choice and carry on", or "wait for a yes". The reader can stop early in three ways: with a progress report that ends the turn, by describing the next step and not taking it, or by asking leave for a step it already has. Name the specific early stop where it costs. Ask only for what the person has not already given. Keep a real ask for a risky or destructive step.

**A fence.** Say what the document leaves alone and where it ends: what it writes and nothing else, what belongs to the next step, that it commits nothing. Close the fence the other way too, so the reader does not under-deliver: "this is about extras only, so do everything the task asks, completely."

**The right freedom.** Where one sequence is safe, such as a destructive or fragile step, give the exact command and say where each value comes from. For work that needs judgement, state the outcome, the constraints and the check, and keep numbered steps only where the order matters. A hand-written script for judgement work does worse than the reader's own plan.

## Wording

- **Normal volume.** No capital MUST, NEVER, CRITICAL or IMPORTANT. Capitals cause rigid, over-applied behaviour.
- **State the bar, and not the pressure.** "Be thorough", "relentless" and "refuse to give up" are followed to the letter, over-work, and can contradict the exit. Write the bar: "try three of these ways before you stop".
- **No hedge on a requirement.** "Try to", "if possible" and "should" are read as leave to skip. Write "Include a summary." A real condition is not a hedge: "run `shellcheck` when it is installed".
- **Never ask for visible reasoning.** No "show your thinking" and no required reasoning section. The turn can end in a refusal. Ask for what was decided, or for a summary of what was done.
- **Do not steer thinking with prose.** No "think harder" and no "don't overthink". Effort is the only control.
- **One word for one thing,** in the document, its reference files, the prompts and the code.
- **Nothing that dates.** No version number, no token count for "a session", no story of the incident behind a rule. Check that each path, command and flag the document names exists and does what the line says.
- **An example is the strongest signal.** The reader copies its length, tone and shape. In a template, mark which text is copied and which is replaced.
- **Shape, and not length, for output.** Where a program or another Session reads the output, fix its shape: the heading it ends under, one line for each item, the fields of a line. A word cap is obeyed, and a report cut to fit can drop an item with nothing to show it. Give the reason to be brief in its place, such as "the whole report is pasted into the next prompt". Where the caller sees only the last message, say what that message must hold. Set no schedule for progress updates.

**Prohibitions.** A ban earns its place when the failure really happens on the model that reads the document, or when it states a real constraint. Then write it well: name the specific thing, give the reason, and say what to do in its place. The reader follows a named, specific "leave this out". A ban on a habit the reader does not have is the kind to delete. Do not turn every ban into a positive, and do not delete a hold-back rule that carries its reason.

**Leading words (guess).** A leading word is a compact concept the model already holds, such as _tracer bullet_ or a loop that is _red_, used as the same token each time. The idea is that it anchors behaviour in few tokens. Nobody has measured it. It is never a pressure word, and where a bar can be stated, state the bar.

## One point, one ruling

When two texts rule differently on one point, the reader may follow either. This is the commonest fault in a document that has been edited over time. Look for it between:

- two lines of the document, or the document and its reference file;
- the document and a skill, a rule or an output style that loads beside it, such as a style that asks for few plain words beside a skill that asks for exact terms or for every finding;
- the document and a later message: a caller's prompt, a script's follow-up;
- the document and the tool: a limit, a permission prompt, a command that is not there;
- the document and the code: what a script really hands over, runs or reads.

Mend it by giving the point one home and pointing at it, or by saying which text wins: "where the testing rule says otherwise, the rule wins". Near-copies in different words count, because the reader spends effort to reconcile them, so state a shared rule in its source's words. Two copies that agree are a cost of upkeep and not a defect. A deliberate recap is allowed.

## A rule that must hold

Something that must hold every time needs a check outside the model: a hook, a permission rule, or a check in the script or the test suite that runs after. Write the sentence too, with its reason, so the reader rarely meets the check. Put anything deterministic in a script and tell the reader to run it. Test a check by breaking the rule on purpose, because Claude Code accepts a hook on an event name that does not exist, in silence.

Back the rules that cost most when broken. A hold-back rule that has its reason and nothing behind it stays as a sentence. A heading or a rule that nothing reads and nobody would miss carries no signal, so leave it out.

## Pruning

- Ask of each line: could the reader already know this? An instruction it obeys by default is a **no-op**. Delete the whole sentence. Whether a line is a no-op is settled by running the document, and not by debate.
- The **environment** is a source of truth: scripts, config, the directory layout, `--help`. A document that restates it is a **cache**, worth its load only when the lookup is costly. Cache what cannot be found by looking: the unwritten convention, the reason, the gotcha.
- Keep each meaning in a **single source of truth**, so a change of behaviour is a one-place edit.
- Check each line for **relevance**. A line goes stale as the code, the tools or the model change, and a stale line is obeyed. Without pruning the default fate is **sediment**: layers that settle because adding feels safe and removing feels risky.
- Borrowed text does not know the repo it lands in. Check each path, tool and layout it assumes.

## Keeping a document true

Check a document again at every model release, because a line that carries weight on one model is cruft on the next. Settle a question by running the document in a fresh Session, several times on each model, and read what the agent did and not what it says it would do. Write the model, the effort and the Claude Code version beside any count you record. `/doctor prompt-audit <path>` reads a file against a list of stale prompt habits, for the model that runs it.
