# Steering is the repo's, and machinery is the plugin's

The Plugin ships two kinds of thing, and they travel differently.

Steering is what tells an agent how this team works and what this repo holds: the rules, the
tracker docs, the review baselines and the Suite. `skillworks-setup` copies it into each repo as
files, and the repo owns it from then on. A team edits its copy to suit itself, and a plugin update
never overwrites it. No skill in the Plugin names a fact about one repo; it reads the fact from the
repo's steering.

Machinery is what runs the loop: the skills, the scripts they drive, the hooks and the output
style. It stays in the Plugin and runs from there. Every repo runs the same code, and a fix reaches
every repo with the next update. The output style is machinery, and the Plugin forces it with
`force-for-plugin`, so it is on wherever the Plugin is and beats any `outputStyle` a repo or a
developer sets. Skillworks is for developers new to Claude, and its opinions are what make it easy
to pick up, so the way Claude reports is one of them.

## Considered options

**Ship the steering in the Plugin, through a `SessionStart` hook.** Rejected. Every repo would get
the same text and no repo could change it, and the rules carry settings that differ per repo. It
would also make the Plugin, and not the repo, the source of what a session loads.

**Copy the scripts into each repo.** Rejected. Each copy drifts from the next, and a fix reaches
none of them.

**Copy the output style into each repo.** Rejected. A team could change how the loop reports, and a
repo copy with the Plugin's name would leave it unclear which one a session loaded.

## Consequences

A forced style holds for the whole session, not only while a Skillworks skill runs. When two enabled
plugins force a style, the first one loaded wins, and the docs do not say what order installed
plugins load in. So the preflight warns, and does not stop, when another enabled plugin forces a
style, because Skillworks could lose that race without a word.
