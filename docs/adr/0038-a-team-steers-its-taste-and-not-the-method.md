# A team steers its taste, and not the method

Where teams really differ, the Plugin's opinion is a default a team can edit. Where the opinion is
how Skillworks works, it is Machinery and no team edits it. So a team knows which is which without
reading every skill, this page lists both.

Steering, seeded into the repo and owned by the team:

- which comments a sweep keeps and which it cuts, in the comments rule
- which code smells a review looks for, in the smell baseline
- the shape and size of a ticket, in the tracker docs
- the rules, the Suite, the Tracker and the Target branch

Machinery, the same in every repo:

- the three review axes, and "cite it or drop it"
- the test-first loop in `tdd`
- the deep-module view in `codebase-design`
- the plain writing in `unslop`, and the forced output style
- the Session trailer on every commit, and auto-memory switched off

## Considered options

**Make every opinion a lever.** Rejected. A team would own a file for each one, and Skillworks would
keep no method of its own. The fixed parts are what make it easy to pick up for a team new to Claude.

**Read the team's file first, and fall back to the Plugin's.** Rejected. A team that never edited a
file would get each new default at once, but what a session loads would then change with the Plugin
version and no commit. ADR 0030 turned that trade down already.
