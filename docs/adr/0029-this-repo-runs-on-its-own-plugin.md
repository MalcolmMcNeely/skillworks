# This repo runs on its own plugin

The skills move out of `.claude/skills/` and into the plugin under `plugins/`, and this repo loads
them the way any other repo would: its `.claude/settings.json` names the marketplace in `plugins/`
and enables the plugin. There is one copy of each skill, and every session here proves the plugin
loads and works.

The cost is the namespace. A plugin skill is typed as `/skillworks:spec-loop`, never `/spec-loop`,
so every skill that names another by its bare name changes with the move.

## Considered options

**Copy the skills into the plugin.** Rejected. `.claude/skills/` would stay the working copy and the
plugin would drift from it, and nothing in this repo would ever load the copy other repos receive.
