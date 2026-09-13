# Skillworks

Skillworks builds, ships and measures Claude Code agent skills. It publishes a catalogue as a
Claude Code plugin marketplace, and it runs a local app for watching how those skills behave.

## Language

### The catalogue

**Catalogue**:
The set of plugins Skillworks publishes. It is the product.
_Avoid_: Library, registry, pack

**Marketplace**:
The git repository a developer adds to Claude Code so the catalogue installs and updates itself.
_Avoid_: Feed, source, channel

**Plugin**:
One installable unit of the catalogue. It holds skills, hooks, output styles and MCP servers.
_Avoid_: Package, bundle, module

**Skill**:
A folder of instructions Claude reads when a task matches it.

**Engine**:
A skill Claude picks up on its own. Its description competes for space in the skill listing, so
engines are capped in number.
_Avoid_: Model-invocable skill, auto skill

**Entry point**:
A skill a developer types. Its description is kept out of the model's context, so entry points cost
nothing to add.
_Avoid_: Slash command, manual skill

### The app

**Studio**:
The local app for watching, authoring and testing the catalogue. It runs on the developer's own
machine because authoring writes files and evals start `claude`.
_Avoid_: Reader, console, dashboard, portal

**Health**:
How each **part** of Studio is doing, in one place. A part is working, starting, off or broken. A
switch nobody flipped is off and not broken, because only one of those is a fault and only one of
them is the developer's to fix. Every part that is not working names the action that would change
it.
_Avoid_: Status, diagnostics, readiness

### Measurement

**Activation**:
One occasion on which a skill fired.
_Avoid_: Invocation, call, run, usage

**Trigger**:
What caused an activation: Claude chose the skill, or a developer typed it.

**Provenance**:
Where a Skill came from and what set it off. Only the events store records it; a Transcript does
not, which is the whole reason there are two stores. A period the store holds nothing for is
labelled missing, never shown as none.
_Avoid_: Lineage, delivery, history

**Gap**:
Which way Provenance fell short, when it did: the store was unreachable, telemetry was never
switched on, the period was genuinely quiet, or it held more events than one read takes. All four
arrive as no Origins at all, so the Gap is the only thing that tells them apart, and each one means
something different for the developer to do.
_Avoid_: Error, empty, null

**Origin**:
One way a Skill was delivered and set off: its Trigger, the place it was loaded from, and the Plugin
and Marketplace behind it where a plugin delivered it. A Skill name with two Origins is two Skills
sharing a name.

**Transcript**:
The session file Claude Code writes to disk. It records every activation with its real skill name
and the tokens that turn spent.
_Avoid_: Log, history, session log

**Ingest**:
Reading the Transcripts into Studio's own store. One **pass** is one sweep of the folder; a pass
reads only what changed unless it is asked to read everything again.
_Avoid_: Import, sync, scrape

**Fault**:
A line, or a whole Transcript, the ingest could not read and stepped over. Faults are counted and
kept, so a gap in the numbers is never read as a fact.
_Avoid_: Error, failure, bad record

**Turn**:
One request to the model, and the tokens it spent. It is the unit of spend. A Transcript writes one
record per content block and repeats the whole usage on each, so a turn is counted by its request id
and never by its records.
_Avoid_: Message, exchange, round trip

**Attribution**:
The link from a unit of spend back to the skill that caused it. A Turn is attributed to the skill
that was in force when the request was made, so the turn that chose a skill belongs to no skill.

**Price table**:
What a million tokens of each kind costs on each model. It is read when a question is asked and
never folded into a stored Turn, so correcting a price never means reading the Transcripts again.
_Avoid_: Rate card, tariff

**Model**:
Which model answered, as the Transcript spells it. It is what a row of the Price table is found by,
and what makes two costs comparable.
_Avoid_: Engine, LLM

**Effort**:
How hard the model was asked to think on a Turn or an Activation. It moves the cost without moving
the Model, so it is reported beside it.
_Avoid_: Reasoning level, thinking budget

**Filter**:
The one way every list narrows: a span of days, a repository and a Skill. The span is counted in
whole UTC days and takes both ends in. A Skill that never fired belongs in the unnarrowed answer,
where its zero says the description may be broken; a filter that asks what happened in one week or
one project leaves it out, because it did not happen there.
_Avoid_: Query, search, scope

**Firing eval**:
A test of whether a skill activates on the prompts it should, and stays quiet on the ones it should
not. Cheap. Applies to every engine.
_Avoid_: Trigger test, discovery eval

**Outcome eval**:
A test of whether a skill's output meets its contract once it has fired. Expensive. Applies only
where a skill promises something observable.
_Avoid_: Quality eval, judge eval

**Contract**:
The part of a skill's output that can be asserted without a model judging it.
