# Order is a fourth alphabet

This supersedes the part of ADR 0007 that names three jobs. Studio now draws a small symbol for four.
**Order** says which way a sorted column runs, and `▲` and `▼` belong to it.

Everything else ADR 0007 decided stands. A symbol still belongs to one alphabet, it may still be
reused inside it, and the test that reads every table and fails when a symbol crosses is unchanged.
This decision uses that rule rather than bending it.

The Sessions table sorts on every column, both ways, so a heading has to say which column the answer
was sorted on and which way it ran. None of the three jobs fits. The mark does not name a page, it
says nothing about how a part is doing, and it did not set a Skill off. Putting it in one of them
would give a reader a shape that means two things, which is the clash ADR 0007 exists to stop.

`↑` was already spoken for: it is Publish, in **identity**. Taking it for a sort direction is exactly
the crossing the test catches, so the new marks are `▲` and `▼`, which no table had.

## Considered options

**Draw no symbol and mark the sorted column with colour or weight alone.** Rejected. A reader would
see which column was sorted and not which way it ran, and colour alone is the failure ADR 0007's own
story opens with.

**Draw the direction as a word in the heading.** Rejected. A heading that grows from "Cost" to "Cost,
dearest first" moves the columns beside it every time a reader clicks.

**Draw a triangle in CSS instead of a character.** Rejected as a dodge. ADR 0007 already treats a
drawn mark as a symbol: the dash in the missing-words table carries the note that it is drawn and so
answers to the alphabets like any other mark on screen.

**Force the mark into `condition`.** Rejected. Ascending is not a condition, and a reader who has
learnt that alphabet reads its shapes as how a part is doing.

## Consequences

`Alphabet` is a closed union, so the set of jobs is written down in one place and a fifth needs a
decision like this one. That is the point: a new alphabet should cost a paragraph, because the
alternative is eight folders each inventing their own again.

The sort marks live with the table they serve, as every other symbol table does, and join the list
the crossing test reads.
