# Skill mechanics

What Claude Code does with a skill. The writing rules are in `SKILL.md` beside this file.

Contents: Who can start a skill. The description. The body. Arguments. Front matter. Files beside the skill. Commands the skill names. Text a program matches. Calls between skills. A skill that many repos run. Checking a skill.

## Who can start a skill

| Front matter | A person, by `/name` | Claude | In context |
|---|---|---|---|
| default | Yes | Yes | The description always, the body once started |
| `disable-model-invocation: true` | Yes | No | Nothing until it is started |
| `user-invocable: false` | No | Yes | The description always, the body once started |

- A **model-invoked** skill pays context load for its description in every Session. In return Claude can start it, and other skills can call it. One whose content is all reference is a home for reference that several skills share.
- A **user-invoked** skill sets `disable-model-invocation: true`. It costs no context. A Skill tool call to it is refused, and a subagent cannot preload it. A script can start it, by putting the slash command in a `claude -p` prompt.
- Pick model-invocation only when Claude, or another skill, has to reach the skill unasked. If only a person or a script starts it, hide it.
- Reference that several hidden skills share lives in a plain file. In a plugin, every skill can reach a file under `${CLAUDE_PLUGIN_ROOT}`.
- Split off a model-invoked skill when a distinct request, in words people really use, should reach it alone, or when another skill has to call it. The new description is permanent context load, so that reach has to be worth it.
- A **router skill** cures cognitive load: one user-invoked skill that names the others and when to type each. It tells the person what to type, and it never calls a hidden skill.

## The description

- For a model-invoked skill it is the whole trigger. Claude picks a skill from its name and description, and reads no line of the body before that.
- Each entry is cut at 1,536 characters, `when_to_use` included. All entries share a budget of 1% of the context window. On overflow every name stays and descriptions are dropped, least-invoked skills first. `/context` shows the listing after the budget is applied.
- Where a neighbour skill exists, say what this one is not for, and name the neighbour.
- Do not make a description pushier, and do not reword one that works, unless a trigger eval fails.
- For a user-invoked skill it is a line in the `/` menu for a person, so keep it to one short line. It never reaches Claude. An instruction that sits only there, such as "Stop", is never given: put it in the body.

## The body

- The whole body enters the conversation at once, as one message, and Claude Code never reads the file again. No part of a body can load later. What should load later goes in a file beside the skill, behind a pointer.
- So write a rule that holds all task as a standing instruction: "run the tests after every edit", and not "run the tests".
- Front matter does not reach the model. Anything the model must read goes in the body.
- After a compaction Claude Code keeps the first 5,000 tokens of each started skill, and 25,000 across all of them, most recent first. So what must survive goes at the top. On a 1M window this bites in a very long Session or after a typed `/compact`. "Under 500 lines" is advice, and no loader enforces it.
- `/compact` summarises the conversation in place. It starts no new Session.
- A running Session picks up an edit to a project or personal skill the next time the skill starts. A body already in context is not refreshed. A plugin skill is not watched: the Session keeps the text it started with.

## Arguments

- `$ARGUMENTS`, `$1` and `$name` in a `SKILL.md` body are replaced with what was typed. Write `\$1` for a literal one. A reference file is not substituted.
- A body with no placeholder gets `ARGUMENTS: <value>` added at its end, and nothing when no text was typed. So every skill takes arguments, whether or not it says so. Say what typed text means. Say too that other text which arrives with the request is not an argument, because a script may add lines of its own after the command.
- Give `argument-hint` to a skill that takes arguments. It shows in the `/` menu and costs no context.

## Front matter

- The opening `---` is line 1 and the YAML parses. Otherwise the skill loads with no fields, so it has no description and never triggers.
- Use only the documented keys, spelt exactly: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`, `compatibility`.
- Claude Code ignores an unknown key with no error, and `claude plugin validate` passes a misspelt one. A misspelt `disable-model-invocation` shows a hidden skill to Claude. Guard the keys with a test of your own.
- `allowed-tools` approves in advance for the turn. It does not restrict. `disallowed-tools` restricts, until the next user message.
- `effort` is the only way a skill changes how hard the model thinks, and `CLAUDE_CODE_EFFORT_LEVEL` in the environment overrides it. A skill that a script runs leaves model and effort to the script.
- `hooks` register when the skill starts and run for the rest of the Session. This is how a skill carries its own check.

## Files beside the skill

- A file beside the skill costs nothing until the reader opens it. This is progressive disclosure, and it is the one way to defer part of a skill: put what only some branches need in its own file, one file for each branch, and give each a pointer that states its condition.
- Link every file in the folder from `SKILL.md` itself, one link deep, and say when to read it. A file with no link is found only by chance.
- The loaded body opens with the skill's base directory, so a plain link to a file in the same folder resolves. Write `${CLAUDE_SKILL_DIR}/file` where the reader has to turn the path into a command or hand it on: a script to run, a file to copy, a path given to a subagent. Write `${CLAUDE_PLUGIN_ROOT}/skills/other/file` for another skill's file. Claude Code fills both in before the model sees the body, with forward slashes. Never ask the reader to work out "the folder above this one".
- The variables are filled in `SKILL.md` only, and `${CLAUDE_PLUGIN_ROOT}` only in a plugin skill. In a reference file they arrive as raw text.
- The Session must also be allowed to read the path. A skill loaded from outside the working folder needs a read rule for its own files, or the read is refused where nobody can approve it.
- Keep one root for one path form. Do not let `./` mean the skill's folder on one line and the user's folder on the next. Name a file of the repo being worked on by its repo path, with no variable.
- The skill's folder is the installed copy. Tell the reader to copy a template out of it before changing it.
- A reference file over 100 lines opens with a table of contents. `SKILL.md` needs none.
- Put anything deterministic in a script, and say whether to run it or read it. A plugin's `bin/` is on `PATH`. A script the reader is told not to edit has to be right, and the body has to say how its functions behave where the reader would not guess it.

## Commands the skill names

- Each Bash tool call is a new shell. The working folder carries over, and shell variables do not. So set a variable in the same call that uses it.
- A command Claude runs has no keyboard. A script that waits on `read` gets end of file. A step that needs a person's hands is run by the person in their own terminal, and writes what it captured to a file that Claude then reads.
- A background command has a time limit that the tool sets. Never promise "no time limit" for one. Start a long job detached, and wait for it with a command that can be started again.
- A permission rule matches a command by its start, and for one tool. A rule for Bash does not cover the same command sent through PowerShell (inferred from refused calls). So name the tool, and give the command in the plain form the rule names: no `cd` in front, nothing wrapped round it, one command for each call.
- A write under `.claude/` is a protected path. It is prompted at the keyboard and refused where nobody watches. Say what the reader does when it is turned down.
- Say when a fetch or a read was already done for the reader, so that it does not repeat one.

## Text a program matches

A test, a script or a grader can match a skill's exact text. Search for each string before you change it. What is matched comes in four kinds:

- A sentence, a heading, a command or a flag that must be there, word for word.
- A word that must not be there, sometimes even inside a longer word.
- A position: the last sentence of a description, several strings inside one paragraph, the first fenced block of the file.
- The front matter: which skills are hidden, and which keys are allowed.

Where a test pins the old words and the change needs new ones, change the test in the same commit. Where the new text can keep the old words, keep them. Another skill, or a page written for people, may quote the text too.

## Calls between skills

- Write "Call the Skill tool with `plugin:skill`", with the full name. A model cannot type a slash command, so "Run /x" and "Follow /x" leave it to guess. A bare name works only while no other skill holds it.
- Say how often: "load it once, and it holds from then on". "Both run on every round", after an order to call a tool, asks for the call on every round.
- Never tell Claude to call a hidden skill, because the call is refused. Tell the person to type it, and name the right door: the version a person runs by hand, and not a hidden step of a loop.
- Two skills loaded together are two texts in one context. Say which one owns a shared point, such as a confirmation that both ask for.

## A skill that many repos run

- A plugin skill is the same text in every repo. So it carries no fact of one repo: no branch name, no test command, no folder layout. It reads the fact from a file in the repo, names that file, and gives the exit for a repo where the file is missing.
- A file that a plugin copies into each repo becomes that team's own. An edit to the plugin's copy reaches every team as a diff to read, so do not edit one for style.
- Vendored text is named in the licence notice. Update the notice when the body stops being upstream.

## Checking a skill

- `claude plugin validate <plugin>` checks the manifest and that the YAML parses. It does not catch a misspelt key.
- `claude plugin details <plugin>` prints each skill's size in tokens.
- `/doctor prompt-audit <path>` reads a skill against a list of stale prompt habits, for the model that runs it. A plugin skill is outside its default scope, so pass the path.
- `claude plugin eval <plugin>` runs cases in fresh Sessions: a request that should trigger, a near miss that should stay quiet, a stop rule that should hold. It covers a plugin only. Its Sessions may have no shell, and then it sees the trigger and the first reads and nothing after them.
- Read an eval as a count and not as a gate. At three runs a case, a skill that triggers nine times in ten fails often by chance. A result at the ceiling cannot show that a change helped, so add a case that can fail.
- For what an eval cannot reach, run the skill by hand in a fresh Session, several times on each model, and read the transcript for the tool calls: the read of a reference file, the Skill tool call, the brief a subagent got, a refused call.
- Triggering is not following. A pass on a trigger case says nothing about the body.
