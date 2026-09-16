# The Map shows 25 Skills, so no Tile's area lies

Every Tile gets at least a fiftieth of the Map, so a Skill that barely fired is still large enough to
read and to click. The Map now shows at most 25 Skills, which is the largest count for which that
floor and its own guard both hold exactly. The Filter and the order key choose which 25.

The floor cannot hold at any size. Fifty-one Skills at a fiftieth each is more than the whole Map. The
code shrank the floor as the count grew, to `min(2%, 0.5/n)`, so the promise quietly weakened past 25
Skills and was half of itself at 50. Nothing on screen and no test said where it stopped holding.

A floor is also a lie about area. With four Skills at 1000, 1, 1 and 0.5, the last is a two
thousandth of the total and was drawn at a fiftieth: forty times too big. Two floored Tiles look the
same size when one may be a hundred times the other, and comparing areas is the whole job of the Map.

A cap makes the rule true instead of writing down where it stops. The floor becomes a flat fiftieth
at every size, and the guard that shrank it is no longer needed.

## Considered options

**Fifty Tiles, and drop the guard.** Rejected. Fifty at a fiftieth each fills the whole Map, so in a
long tail every Tile sits on the floor and they are all the same size. More Skills on screen, and no
picture left.

**Mark a floored Tile on screen.** Rejected. In a real catalogue the long tail is mostly floored, so
the mark would cover most of the Map and make the glance harder rather than truer.

**Write the limit down and leave the Map alone.** Rejected. It keeps a Map whose areas cannot be
trusted and asks the reader to remember when.

## Consequences

A Skill is off the Map for one of two reasons, and they are not the same. It had no figure to be
sized by, or it had a figure and did not fit. Each reason gets its own line beneath the Map, naming
the Skills.

A reader who wants the tail flips the order key. Nobody looks at the middle.
