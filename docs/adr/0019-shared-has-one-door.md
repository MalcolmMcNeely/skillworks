# Shared has one door

This supersedes ADR 0018, which let code into `Shared` two ways: by naming a word from `CONTEXT.md`,
or by having no domain meaning at all. The second way was never checked, because whether a piece of
code means anything is a judgement. Writing `shared-names-a-word` and running it over the repository
showed what that unchecked half was holding: fifteen folders. Seven were plurals of words already
settled, such as `Filters` and `Gaps`. Four named things Studio shows and had simply never been
settled. Two named the machinery a test stands Studio up on. Only two, `http` and `palette`, were
plumbing at all. So `Shared` has one door. Every folder in it names a word from the glossary of the
context that claims it, and a folder named in the plural of a headword counts, because a folder
holds many of a thing.

The glossary grows to cover the plumbing rather than the check looking away from it. `Figure`,
`Alphabet`, `Key`, `Page`, `Palette`, `Wire` and `Harness` are settled words now, each with what it
beat. `http` is renamed to `wire`, because `wire` says what the code does and `http` says only which
protocol it does it over.

## Considered options

**Keep the second door as text**, as ADR 0018 had it. Rejected. A rule half a check can read is a
rule an agent reads half of. The count was the evidence: the unchecked half was carrying six folders
that had a domain meaning and needed a word, and it carried them quietly for as long as nobody
looked.

**Ban plumbing from `Shared` and give it a top-level folder of its own.** Rejected for the reason
ADR 0018 rejected it: it splits the first level between jobs and machinery again, and the reader is
back to guessing which is which. It is also a bigger price than two glossary entries.

**Accept only an exact headword, and rename every plural folder to the singular.** Rejected. Half
the folders that failed hold many of one thing and read wrong in the singular, and a check that
makes the tree read worse is a check nobody will keep. The plural is the same word, so the check
learns English instead.

**Let the check read a word from anywhere in the folder name**, so `HealthReport` passes on `Health`.
Rejected. It waves through any name that merely holds a settled word, which is most names, and the
door stops being a door.

## Consequences

The glossary now holds words a reader never sees, such as `Palette` and `Harness`. That is the price
of one door, and it is a small one: each entry says what the word beat, so the next agent picks the
same word rather than inventing a synonym.

A new piece of `Shared` code costs a glossary entry before it costs a folder. That is the order this
repository already wanted, and ADR 0017 set it for Slices. It now holds for `Shared` too.

`shared-names-a-word` joins the run, so a folder with no word fails `dotnet test`. Every check the
Slice work wrote is now in the run, so the staging hatch that held a rule out of it is gone.

The check knows three plural endings and no more: a trailing `s`, `ies` for `y`, and `es` after a
hiss. `Leaves`, `Heroes` and `Indices` would each be turned down. The next folder that needs one of
those teaches the check that ending, and until one arrives the check stays as small as the tree
needs it to be.
