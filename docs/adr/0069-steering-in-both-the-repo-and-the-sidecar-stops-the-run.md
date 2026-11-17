# Steering in both the repo and the Sidecar stops the run

A repo's Steering sits in one place: the repo, as part of what a developer delivers to a client, or the
Sidecar, for a client that must see no trace of Skillworks. When both hold a `loop.json`, preflight
stops the run and names the two, and each Session warns. The developer removes one.

It happens once for a client, when a Sidecar client takes the Steering into its repo. Before this the
Sidecar won without a word, so a run read the old copy while the repo held the new one.

This amends ADR 0064.

## Considered options

**The repo wins.** Rejected. The Sidecar copy is then dropped without a word, the same fault the other
way round.
