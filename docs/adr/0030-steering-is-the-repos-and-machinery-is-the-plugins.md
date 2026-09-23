# Steering is the repo's, and machinery is the plugin's

The Plugin ships two kinds of thing, and they travel differently.

Steering is what tells an agent how this team works: the rules, the tracker docs and the output
style. `skillworks-setup` copies it into each repo as files, and the repo owns it from then on. A
team edits its copy to suit itself, and a plugin update never overwrites it.

Machinery is what runs the loop: the skills and the scripts they drive. It stays in the Plugin and
runs from there. Every repo runs the same code, and a fix reaches every repo with the next update.

## Considered options

**Ship the steering in the Plugin, through a `SessionStart` hook.** Rejected. Every repo would get
the same text and no repo could change it, and the rules carry settings that differ per repo. It
would also make the Plugin, and not the repo, the source of what a session loads.

**Copy the scripts into each repo.** Rejected. Each copy drifts from the next, and a fix reaches
none of them.
