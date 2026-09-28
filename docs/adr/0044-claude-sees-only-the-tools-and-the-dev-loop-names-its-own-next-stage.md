# Claude sees only the tools, and the Dev loop names its own next stage

Claude sees the description of every skill it may start, and never the description of a skill that
sets `disable-model-invocation: true`. `spec-loop` and the Grill set it, and `to-tickets` and
`implement` did not. So when a spec was published, Claude suggested the two next steps it could see,
and never `spec-loop`, the one the Dev loop wants. So `implement` and `to-tickets` set the flag too,
and Claude no longer sees them. The driver types `/skillworks:implement` in each Session, as it did,
and it now cuts a spec's tickets itself, as a step of its own that types `/skillworks:to-tickets`,
because nothing may call a hidden skill through the Skill tool. A developer can still type any of
them. The tools, such as `tdd` and `review-changes`, stay open to Claude. `to-spec` stays open too,
because the Grill calls it through the Skill tool, and its description points at the Grill instead.
Each stage of the Dev loop names only the next stage.

Three runs of `claude -p` on 2026-09-28, against a throwaway plugin, decided it. A hidden skill ran
when its command was typed. The Skill tool refused to call a hidden skill, and said: "Do not
replicate this skill's workflow by other means". A skill that read a hidden skill's file, to follow
it, was refused the read, because the plugin's folder sat outside the repo.

## Considered options

**The calling skill reads the hidden skill's file and follows it.** Rejected. It works only once a
read rule opens the plugin's folder, and it goes around what Claude Code means the flag for, which is
a skill run only when a person asks. A later version of Claude Code could close it.

**Every flow step stays visible, with a "Not for" line in its description.** Rejected for
`implement` and `to-tickets`. A line of text asks Claude not to suggest them, and the flag makes sure
it cannot. It is kept for `to-spec`, the one step the Grill has to call through the Skill tool.

## Consequences

A skill's own extra files were never readable in a loop Session when the Plugin sits outside the
repo, as it does in every repo but this one. So setup's allowlist now opens `~/.claude/plugins/`,
and a Marketplace folder outside the repo, to reading.
