---
name: write-generation-prompt
description: Write or change the prompt an app sends a model to generate text for its users, such as summaries, replies or descriptions. Use when outputs read wrong, invent facts or ignore a rule, when adding a field, a mode or a rule to the prompt, or when output made from a source text should follow that source more closely. Not for eval judges, which is write-judge-prompt, and not for documents an agent reads, which is skillsmith.
argument-hint: "[what is wrong, or what the prompt should do]"
---

You produce a change to a text-generation prompt and an eval result that shows whether the change helped. The typed text says what is wrong or what the prompt should do, and may name a ticket or spec. Other lines that arrive with the request are not arguments.

In this skill, an **output** is one text the model returns for one case. The **generation call** is the model call whose output an eval scores, and an **eval judge** is the model call that scores it.

Before you write any prompt text, call the Skill tool with "skillworks:skillsmith", once, because a runtime prompt is a document a model reads and skillsmith's wording rules hold for it. On one point this skill wins: a real limit on an output field, such as a field size another system enforces, is a format rule. Keep that limit, with its reason, even though skillsmith warns against word caps.

## Map the app

This skill holds no fact about any one app. The code and the repo's own docs are the source of truth, so read them fresh on every run rather than trust a summary written earlier. Answer each question below and give a `file:line` or a quoted doc for each answer. Where the code and a doc disagree, the code wins. Name the doc that is wrong.

1. Where does the prompt text live, and how does code assemble it: its parts, their order, and its modes?
2. What is the input's shape, and what else reads that shape, such as the evals?
3. What is the reply type, and how does it become a schema?
4. Where is the call made? Which model, provider and settings does it use?
5. Which user-facing doc describes the output?
6. What are the build and test commands? The repo's agent instructions or its README say.
7. How do you run the evals for this prompt? Read the docs beside the eval code, and answer each part:
   - What is the quick run they describe, the cheapest run that still yields outputs and scores?
   - How do you narrow a run to some of the cases?
   - Where are the outputs stored?
   - Does the harness cache replies?
   - Do the repo's own instructions limit eval runs, such as for loop work?

   Say so if there are no evals, or if the docs describe no quick run.

A question you cannot answer is reported as "not found", with where you looked. Do not guess.

**Intent** is what the owners of the app have settled about the output. Code cannot show it. Take it from the request, from a ticket or spec the request names, or from the prompt itself. If the work depends on a point that none of these settles, ask the person and wait.

Once a point about the output is settled, write it into the prompt, where the model reads it. A point about the evals goes in the eval docs. Keep neither in a side file, because a copy goes stale while the prompt and the eval docs stay true. A prompt line that disagrees with a settled point is a fault to fix.

## How each eval run runs

Read [eval-runs.md](eval-runs.md), and run every eval run as it says.

## Before you change anything

1. **Find the fault in real outputs.** Quote two or three stored or fresh outputs that show it. If no output shows it, say so and stop, because a rule against a failure that does not happen can pull the model toward it.
2. **Take a baseline with the quick run.**
   - **What to run.** Before any edit, run the eval docs' quick run, narrowed to the cases your change touches. Use only the model the app uses in production. Record the run name and its exact settings.
   - **Why it is cheap.** Every later run uses the same settings, so each comparison is a quick run against a quick run, like for like.
   - **Reuse.** When the harness caches replies, a rerun with nothing changed reads from the cache, so first look for a stored run with the same settings and reuse it.
   - **No quick run in the docs.** Build the cheapest run from the options the docs list: the fewest iterations, one model, only the touched cases. Say in the report that you built it.
   - **No evals.** Stop. Name what is missing: the code that runs the generation call over cases, the stored outputs, or the call to the eval judge. Say that no change can be measured and that nothing was written. Ask the person whether to build evals first (`write-judge-prompt` covers the eval judge side) or to go ahead unmeasured, and wait for the answer.

## Provider questions

Read [provider-questions.md](provider-questions.md), and answer its questions as it says. Write the prompt and the reply type to fit the answers.

## Writing the prompt

**How the model reads.**
- The model follows the text literally, and does what is asked and little more. So state the scope of each rule, and put its reason beside it, because the model extends a rule only as far as its reason goes.
- Use normal volume, with no capital MUST or NEVER.
- Tell the model who reads the output and what a bad output costs them. That context steers it more than adjectives do.

**One point, one ruling.**
- When code joins several parts, a part that contradicts another leaves the model to pick a side.
- When a mode has to override a shared rule, leave that rule out of the mode's prompt. Move the rule into its own part, and have the assembling code drop it for that mode.
- A line such as "this part wins" leaves both rulings in front of the model, so it is the weaker fix.

**Voice.**
- Describe concrete writing choices, with reasons: who the text talks to, how sentences open, and what comes first.
- A label such as "warm" or "fun" gives the model little to act on.
- Name a pattern to avoid only after a real output has shown it.
- Do not set numeric style rates, such as "one sentence in three ends with !". The model follows them too closely and the prose turns choppy. Measure rates in the evals instead.

**Examples.**
- Use 3 to 5 examples, varied, and say they are illustrations.
- The model copies an example's length, shape and phrases, so it copies a lone example of a kind too closely.

**Output made from a source text.** When the output has to follow a source closely, the source is the only example. Generic voice rules and worked examples pull the output away from it, so leave them out of that mode. Two designs exist. Measure both before choosing:

- **A mode prompt.** The prompt asks for the source with only the untrue parts changed.
- **Substitution pairs.** The model returns `{find, replace}` pairs, and code applies them to the source.
  - Code checks that each `find` occurs once.
  - A `replace` may cover a whole phrase, so articles and plurals stay right.
  - The rest of the text cannot change.
  - This design needs a new reply type and new code, so propose it before you build it.

**Facts.**
- Every claim comes from the input.
- Give the model a way out when facts are thin, such as an empty field or a list of missing facts. Never leave invention as the only way to obey.
- Anything that has to hold every time needs a check in code after the call, such as a required notice, a number that must match the input, or a name that must not appear. Propose that check.

**Text from people.**
- Source texts and user notes are data a person supplied, so wrap each one in a named tag.
- In the prompt, say what each one may change and what it may not. For example, a note may change tone and focus, but never facts or required lines.

**Length and format.**
- Put a real field limit in the prompt as a format rule, with its reason.
- Check the limit in code after the call, because a model misses counts.
- Shape the reply with the provider's structured output, and not with prose that asks the model for a format.

## Checking the change

- **One change per run.** Name each run after its change, and use the baseline's exact settings. Several changes in one run cannot be told apart.
- **The outputs decide.** A quick run shows no spread, so it can show a large change and nothing smaller.
  - Read the outputs of the cases you meant to fix. Read the same cases in the baseline.
  - Count the outputs that still show the fault and the outputs that show a new fault.
  - Treat a small move in the mean score as "no clear change".
- **Quote one output before the change and one after,** for the fault you fixed.
- **A removal is a hypothesis too.** If a cut made things worse, put the line back in its shortest form.
- **Build and test** with the commands you found.

This skill changes the prompt parts and the code that assembles them. It changes the reply type, the call code and the user-facing doc only when the person agrees. It leaves eval judges alone, because an eval judge change in the same pass makes the scores impossible to compare.

## The report

End with a message that holds every item below:

- What changed, file by file, and the fault each change mends.
- The baseline and new run names, their settings, the mean score of each, and your fault counts from the outputs. Name any limit from the repo's own instructions that set the run size.
- One output before the change and one after.
- Each provider question you answered, its answer, and the URL that gave it.
- Each map answer you could not find, and each doc that disagreed with the code.
- Each question still waiting for the person.
