# A rule setting has a value for each common choice

The meaning of a rule setting lives in Machinery: `/skillworks:architecture-tests` builds each check
from the Plugin's own table, not from the team's prose. So a team whose choice no value names can
only write prose that disagrees with its check. Each setting a check reads therefore has a value for
each choice a common repo makes, and the values are names that say what they do. A team changes its
rule file, and never has to change a generated test to get the meaning it wants.

A value that is renamed is a hard switch. The old value is dropped, and no alias keeps it. A rerun of
`/skillworks:architecture-tests` names each test that still reads an old value, because a rerun does
not rewrite a test the team owns.

## Considered options

**The team edits the generated test.** Rejected. The team owns that test and may change it, but the
rule file is what a developer reads and edits. The setting's value would then say one thing and the
test do another, and a rerun for a new language writes the Plugin's meaning again.

**Keep the old values as aliases.** Rejected. Few repos use the values a rename drops, and a rule
that lists old names beside new ones is harder to read, which is the fault this decision fixes.

**Add a setting for every case a repo might hit.** Rejected. A setting joins only when a real repo
fails a check that no value can fix. Each setting is one more thing a developer has to learn.
