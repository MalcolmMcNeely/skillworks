# The README changes only as its Surface item says

The loop grew this repo's README one ticket at a time. Each spec that said "the README says X", and
each builder that documented its change where a newcomer would see it, added a sentence, until the
page was a long reference nobody read to the end. Most of those commits came from tickets, although
the README was never one of this repo's Surfaces. A README is a pitch and a way in. Only a focused
session writes one well.

So the README Surface, found by its heading `## The README`, is the one route by which the loop
changes the README. A spec names the README only in its Surfaces section. The `spec` review removes
any README edit its README item does not ask for. How much an item may ask for is the Surface's
"What to capture", which the team owns. The Seed allows a line that changes and one new item in the
setup or run steps, and never a new sentence or section. The drift check reads the README on every
spec, and a link, path or command the spec broke is a Gap, so a rename the grill missed is still
caught. A change that deserves new README text goes into the spec's Out of Scope as a focused session,
and nothing builds it. A repo with no README Surface gets none of these rules.

## Considered options

**Remove the README Surface.** Rejected. The appending never came from the Surface, and without it
nothing would catch a rename that left the README naming something gone.

**The landing refuses a ticket that changes the README.** Rejected. A script cannot tell a rename from
a new paragraph, and the Gap and rename tickets have to touch the README.

**The loop never touches the README.** Rejected. The README would be wrong between focused sessions,
and a wrong setup step is the worst error a README can hold.

**The Plugin fixes the limit.** Rejected. How much the loop may write in a README is taste, and a team
steers its taste. That the item is the only route is method, so the Plugin fixes that part.
