# Every symbol belongs to one alphabet

Studio draws a small symbol for three different jobs. **Identity** names a page. **Condition** says
how a part is doing. **Cause** says what set a Skill off. Eight feature folders each kept their own
table of symbols and none knew about the others, so six symbols came to mean two things at once. A
symbol now belongs to one alphabet and may be reused only inside it. A test reads every table and
fails when a symbol crosses.

No single ticket could see the clash. It showed only once Home put a page's symbol and a Health Lamp
on one screen: `●` was Watch in cyan and a working part in green, told apart by colour alone. `◈` was
Home and "Given to an agent". `✦` was Author and "Claude chose it".

Reuse inside one alphabet is what a reader wants. `✕` already means broken, missing, unreachable and
unlinked in four places, and it says the same thing every time.

## Considered options

**One shared table of symbols.** Rejected. It would pull `pages`, `health`, `provenance` and
`telemetry` into a dependency none of them otherwise needs, so that four folders could share a
constant. A folder may name its own things. What it may not do is take a symbol the screen has
already given away.

**Fail on any repeat.** Rejected. `✕` would have to change in three of its four homes, and the screen
would lose a symbol that is doing its job.

## Consequences

The pages gave way in all three clashes, because a page symbol is only a label, while a filled dot is
a lit lamp and a sparkle is Claude choosing. The page symbols are now a named table where they were
five bare arguments inside a builder call, and they read `⌂` Home, `▦` Watch, `✎` Author, `✓` Test,
`↑` Publish.

Every table names the alphabet it belongs to, so the test has something to read. A word that never
leaves its folder and never reaches the screen is not covered by any of this. It is the folder's own
business.
