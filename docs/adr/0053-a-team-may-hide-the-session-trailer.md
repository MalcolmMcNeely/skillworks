# A team may hide the Session trailer

The `Skillworks-Session` trailer stays on by default, but a team that does not use the telemetry
behind it can turn it off. `session-trailer` in `docs/agents/loop.json` is `show` or `hide`, in the
same shape as `co-authored-by`. With `hide`, neither the hook nor the Keep writes the trailer, and
the hook no longer refuses a commit for want of a Session id. Not every team buys into a method
built on reading Sessions back from telemetry, and a trailer that leads nowhere for them is only
noise in their history. Nothing in the loop reads the trailer, so hiding it breaks no step.

This amends ADR 0031, ADR 0038 and ADR 0046. The Session trailer moves from Machinery to Steering.
The `Ticket` trailer stays Machinery, with no switch.

## Considered options

**A switch for every trailer.** Rejected. Land checks the `Ticket` trailer, and the drift check, the
Name check and the Export find a spec's commits by it, so a loop without it cannot run.

**No switch, and leave the trailers to the Export.** Rejected. The Export cleans only the branch a
person hands to the client. With the `github` Tracker the Target branch sits on the client's remote,
where the team sees every commit the loop made.

**Setup asks about it.** Rejected. The default suits a team that uses the whole Plugin, and a team
that wants `hide` edits one line.
