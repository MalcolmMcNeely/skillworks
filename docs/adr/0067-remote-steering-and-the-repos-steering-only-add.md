# Remote Steering and the repo's Steering only add

A developer who works for a client keeps two kinds of Steering. Their remote Steering holds their own
way of working, which they keep and the client never gets. The repo's Steering holds what is true only
in the client's repo. It is part of what the developer delivers, and the client owns it when the
developer goes.

The two Layers only add. Neither replaces a section, a bullet, a table row or a sentence of the other,
and each part of the text a step reads comes from exactly one of them. When both hold a file at the
same path, the step reads one file: the repo's text, then the remote's. Settings stay in the repo,
because a YAML block is a fact about one repo, so a remote file that holds one stops the run. Path
rules stay in the repo for the same reason: a path rule names paths in one repo. Skillworks does not find or
settle a conflict between them. The developer writes both, so the developer keeps them from
conflicting. Jakks is the first case: a rule of one class per concept conflicts with the client's own
code style, and the developer changes one of the two texts.

## Considered options

**The repo's Steering replaces a remote section of the same name, and an empty one removes it.**
Rejected. The client repo would then name every rule the developer turned off, so the method leaks out
through its own exceptions. A table row or a sentence cannot be replaced alone, so the client copy has
to hold the rest of the section, and that leaks more. The merge also needs rules for headings, bold
bullets and YAML keys that adding does not.

**The remote Steering keeps a place for each client, with the changes to the method for that client.**
Rejected. One developer writes both Layers, so a conflict is theirs to avoid when they write, and a
place for each client is machinery for a problem one person already controls.
