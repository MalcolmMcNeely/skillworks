# Steering lives in one folder

Every file of a repo's Steering lives under `docs/agents/`, so a team finds all of it in one place.
Some of it has to be in every session from the start, and the rest only when a skill reads it. The
rules are that first kind, and `CLAUDE.md` loads them with an `@` import each, so the split stays
while the folder is one. The preflight checks that each import is still there, because deleting one
line would otherwise turn a rule off without a word.

The files a tool or a design places stay where they are: `CLAUDE.md` and `.claude/settings.json`,
the glossaries and the ADRs, and a linter's own config.

## Considered options

**Keep the rules in `.claude/rules/`, and list every file in a map.** Rejected. Claude Code loads
that folder on its own, so no import can go missing, but a team would still look in two places.

**Put all of it under `.claude/`.** Rejected. Claude Code treats a write under `.claude/` as a
protected path, and only bypass mode lets the loop make one. The loop's default stays `acceptEdits`,
and a ticket that adds a Suite check or updates a baseline has to be able to write its Steering.

**Put all of it in `.claude/rules/`.** Rejected. Every session, and every step of the loop, would
carry the reviewers' baselines too, and the loop still could not write there.
