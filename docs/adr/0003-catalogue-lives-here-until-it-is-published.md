# The catalogue lives in this repo until other people install it

The catalogue ships as a Claude Code plugin marketplace, which is a git repository developers add
and Claude Code clones. It will live at `plugins/` here, beside Studio, rather than in a repo of its
own. One repo, one build, one version, and no cross-repo testing before there is anything to test.

The cost is real and it has a date on it. A marketplace install clones the whole repository, so
every consumer would pull Studio's React and C# source to get a folder of Markdown. That is
harmless while the only consumer is this machine. Other developers will eventually consume
Skillworks as a published plugin, and that is the trigger to split `plugins/` into its own
repository.

Studio therefore takes the catalogue path as configuration from day one, defaulting to `plugins/`
here. Nothing in the app assumes the two live together, so the split stays a move rather than a
rewrite.
