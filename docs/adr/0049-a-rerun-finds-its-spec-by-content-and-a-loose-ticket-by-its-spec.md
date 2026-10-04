# A rerun finds its spec by content, and a loose ticket by its spec

`tracker-publish` can be run again after a run that failed on the network, and it must find what
that run filed rather than file it twice. The failed run may have made the issue and never heard its
number back, so the rerun has no number to look for. It needs something it knows before it files.

With `github`, a spec is now found again by a hash of its title and its body, written in a hidden
HTML comment on the first line of the body. A rerun with the same spec file finds its own issue. A
spec with the same title and a different body gets an issue of its own, and the command says which
open spec shares its title. A ticket is still found by its title among its spec's sub-issues. A
ticket filed before a failed link has no parent yet, so it carries its spec's number in a hidden
comment on its first line, and the rerun matches a loose ticket by its title and that number.

## Why

In the retest of 4 October a Grill published a spec whose title matched an older open spec, from a
run that had ended hours before. The command matched by title, returned the old number and wrote
nothing. The Grill told the developer the spec was published as that number, and the driver ran the
old design. The driver does not close a spec when a run ends, so an old spec can wait open a long
time for a new one to share its title. Two Grills that pick one title at about the same time meet
the same fault, and the second spec is lost with no error.

## Considered options

**Match a spec by its title.** Rejected. It is the fault above.

**Keep the hash in a label.** Rejected. A label holds 50 characters and a sha256 hash needs 64.

**Keep the hash in a comment on the issue.** Rejected. It is a second call after the issue is made,
so a failure between the two leaves an issue a rerun cannot find.

**Hash each ticket as well.** Rejected. A Gap ticket and a rename ticket hold text a fresh Session
writes on each run, so a rerun sends a different body. A hash would never match them, and each rerun
would leave a stray open ticket. What a loose ticket lacks is which spec it serves, not its content.

**Fall back to the title for an issue with no hidden line.** Rejected. Every open spec filed before
this change would keep the fault. A rerun that spans the change files once more, one time only.

## Consequences

The hidden lines stay in every issue the command files. A change to their format means the issues
filed before it no longer match, so the format is held as it is.
