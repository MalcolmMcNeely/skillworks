# A repo names its one ADR folder and owns its ADR shape

A team that tries Skillworks on a repo that already keeps decisions should get new ADRs where its
own ADRs live, in the shape its own ADRs take. So `adr-folder`, in a YAML block at the end of
`docs/agents/domain.md`, names the one folder every new ADR goes to, and both the scripts and the
skills read it. The prose above the block may name other folders for a reader. No folder belongs to
one context any more: a decision about one context goes to the same folder as every other.

A new ADR takes the highest number in the folder plus one, padded to the width of the
highest-numbered ADR there, so a team that numbers `001` gets `003` and not `0003`. An empty folder
starts at `0001`. The shape is Steering, in `docs/agents/adr-format.md`, seeded with the Skillworks
shape as the default. When to offer an ADR stays in the skill, because a team steers its taste and
not the method (ADR 0038). Context backfill's Drafts are written in that shape by the model, and
its script adds only the numbers.

Preflight stops on a `domain.md` with no `adr-folder`, because a missing setting would quietly make
`docs/adr/` beside the team's real folder. Setup asks for the folder and suggests one it finds: a
folder of numbered Markdown files with `adr` or `decision` in its path.

## Considered options

**A list of folders, where writers take the first.** Rejected. The readers are models, and prose
already tells them where else to look, so the list would only hide a rule about which folder wins.

**A key in `loop.json`.** Rejected. A team looks for its domain docs in `domain.md`, and the two
files could disagree.

**Read the folder out of the prose.** Rejected. A team that rewords the prose breaks the parse.

**A folder for each context, named in the context map.** Rejected. Nothing handled it but prose,
and no repo used it.

**Always pad to four digits.** Rejected. A new ADR would sort out of place in a folder that pads
to three.

**Copy the shape of the folder's highest-numbered ADR.** Rejected. A model copies a shape well, but
the script would need a rule for every shape a team can write.

**The script builds each ADR from the template.** Rejected for the same reason.
