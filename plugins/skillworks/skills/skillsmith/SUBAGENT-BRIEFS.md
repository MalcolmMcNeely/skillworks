# Subagent briefs

What holds when the document is a brief for a subagent, a subagent definition, or a line that tells the reader to start a subagent. The writing rules are in `SKILL.md` beside this file.

- A subagent knows only its brief. It does not see the conversation, the skills already loaded or the files already read. `Explore` and `Plan` also skip `CLAUDE.md`, and `Explore` reads excerpts. A subagent may run on another model.
- So say what the brief holds, and that it is pasted in and not pointed at: the question as the user put it, what is already settled or ruled out, the vocabulary, absolute paths, what to leave alone, and what comes back.
- Say which agent type, with the reason. Say how many, as a number. To run several in parallel, start them in one message.
- The subagent's last message is all the caller gets, and the user does not see it. Fix what it holds, and tell the caller to pass it on.
- Say who records a result that several subagents produce. One shared thing has one writer.
- A subagent can call the Skill tool. Where it must have a skill, name the skill in full in the brief, or list it under `skills:` in the subagent definition, which loads the body at the start. A hidden skill cannot be preloaded.
- A skill can be loaded inside a subagent. A line in it such as "start a background agent" says who it is for: the main conversation starts one, and an agent that was started to do the job does the job itself.
- `context: fork` in a skill's front matter runs the body as a subagent's prompt. That subagent does not see the conversation, so use it only for a skill that holds a whole task and needs nothing the conversation holds.
- A hand-off or a summary for a fresh context says what it must keep: what was asked, what was decided or ruled out, each constraint, the state of the work, and the next step. Ask for what was decided, and never for the model's reasoning.
- Do not rest a guarantee on a rule given to a subagent. A lead agent can invent the user's consent to get past a subagent's refusal.
