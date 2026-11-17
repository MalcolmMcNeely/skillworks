# Remote Steering and the repo's Steering only add

A developer who works for a client keeps two kinds of Steering. Their remote Steering holds their own
way of working, which they keep and the client never gets. The repo's Steering holds what is true only
in the client's repo. It is part of what the developer delivers, and the client owns it when the
developer goes.

Some of the developer's way of working does not fit one client. Jakks is the first case: a rule of one
class per concept conflicts with the client's own code style. That exception is the developer's
decision, so it lives in their remote Steering, in a place kept for that client.

So the two Layers only add. Neither replaces a section, a bullet, a table row or a sentence of the
other, and each part of the text a step reads comes from exactly one of them.

## Considered options

**The repo's Steering replaces a remote section of the same name, and an empty one removes it.**
Rejected. The client repo would then name every rule the developer turned off, so the method leaks out
through its own exceptions. A table row or a sentence cannot be replaced alone, so the client copy has
to hold the rest of the section, and that leaks more. The merge also needs rules for headings, bold
bullets and YAML keys that adding does not.
