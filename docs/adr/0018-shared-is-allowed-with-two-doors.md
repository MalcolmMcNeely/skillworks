# Shared is allowed, with two doors

`shared` has been on `banned-folder-names` beside `utils`, `helpers`, `common` and `misc` since the
placement rules were written, because a folder named for nothing fills with anything. But code that
no single Slice owns is real — the two store readers, the Filter every list narrows by, the words a
Gap is reported in — and naming each of those at the top level puts technical folders back beside the
jobs, which is the thing Slices are meant to fix. So `Shared` comes off the ban, at the top of a code
root only, and the discipline that replaces the ban is written into the rule.

Code gets into `Shared` one of two ways. It names a word from `CONTEXT.md`, or it has no domain
meaning at all. The first is checked against the glossary's headwords. The second is a judgement no
check can make, so it stays as text, in the way the ordinary comment rule does.

The test runs on the piece, not on the word. Only what two Slices actually read moves. `Skill` is a
glossary word, but only the list of Skill names the filter offers goes to `Shared`; the Map, the
Tiles and the skill report stay in Watch.

## Considered options

**Keep the ban and name each shared folder for what it does**, at the top level beside the Slices.
Rejected. It splits level one between jobs and machinery again, and the reader is back to guessing
which is which.

**Let a headcount decide: two Slices use it, or it moves out.** Rejected. It waves `http` and
`palette` through on a technicality and throws out `Catalogue`, which is a glossary word only one
Slice reads. Counting users asks how popular a thing is; the glossary asks what it means, and meaning
is the question.

**Two folders, one for words and one for plumbing.** Rejected for the same reason as the first: it
divides the top level again.

## Consequences

`common`, `utils`, `helpers` and `misc` stay banned everywhere, and a lowercase `shared` stays banned
below the first level, so the ban still does the work it was written for.

`Shared` never reads a Slice. The arrow runs one way, so a Slice can be read in full without opening
anything above it.

Half the door is unchecked. Claude can still put something in `Shared` that has a domain meaning and
names no glossary word, and only a review will catch it. That is the price of letting the folder
exist at all, and it is smaller than the price of pretending the code it holds belongs to a job.
