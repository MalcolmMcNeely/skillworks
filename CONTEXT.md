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
machine because authoring writes files and evals start `claude`. What it measures it reads from the
organisation's Events store, never from the machine it runs on.
_Avoid_: Reader, console, dashboard, portal

**Health**:
How each **part** of Studio is doing, in one place. A part is working, starting, off or broken. A
switch nobody flipped is off and not broken, because only one of those is a fault and only one of
them is the developer's to fix. Every part that is not working names the action that would change
it.
_Avoid_: Status, diagnostics, readiness

**Lamp**:
What Health shows for one part: a symbol, a word and a colour. The symbol alone says which state the
part is in, so colour is never the only signal.
_Avoid_: Indicator, light, badge

**Home**:
The page Studio opens on. It holds a panel for each of Studio's jobs, Watch, Author, Test and
Publish, and leads to the ones that are built.
_Avoid_: Landing page, start page, index

**Watch**:
Studio's first job, and the page that does it: which skills fire, how often, in which Repositories,
and what they cost.
_Avoid_: Dashboard, summary, overview

**Map**:
The picture Watch draws: one Tile for each Skill, sized by the figure the reader picked. It shows
the largest 25 Skills, so every Tile's area is true. A Skill it leaves out is named beneath it, with
the reason.
_Avoid_: Treemap, chart, grid

**Tile**:
One Skill's place on the Map. Its area is that Skill's share of the figure the Map is sized by, and
never less than a fiftieth of the Map, so no Skill is too small to read or to click.
_Avoid_: Cell, box, block

### Measurement

**Telemetry**:
The events Claude Code sends while it is switched on. Everything Studio measures is telemetry.
_Avoid_: Usage data, metrics

**Events store**:
The organisation's store that Claude Code's telemetry events arrive in, once telemetry is switched
on. It is the only place Studio reads what it measures. Studio keeps nothing of its own.
_Avoid_: Event log, telemetry store, transcript store, database

**Activation**:
One occasion on which a skill fired. It holds only what Claude Code said when the skill fired: the
skill, the time, its Origin, its session and its Repository.
_Avoid_: Invocation, call, run, usage

**Trigger**:
What caused an activation: Claude chose the skill, a developer typed it, another skill called it, or
an agent preloaded it. All four are Activations, but only Claude choosing a skill is evidence that
its description works.

**Provenance**:
Where a Skill came from and what set it off.
_Avoid_: Lineage, delivery, history

**Gap**:
Which way an answer from the Events store fell short, when it did: the store was unreachable,
telemetry was never switched on, or the period was genuinely quiet. Each can arrive as nothing at
all, so the Gap is the only thing that tells them apart, and each one means something different for
the developer to do. Whether telemetry is
switched on is read from the machine Studio runs on, so that Gap speaks for this machine only. A
period the Events store holds nothing for is labelled missing, never shown as none. A store that stops
answering part way keeps the days already read, and the Gap names the days it could not read.
_Avoid_: Error, empty, null

**Arriving**:
An answer from the Events store that has not finished reaching the screen. What has landed is shown at
once, and its figures can still grow. It is **complete** when its last part lands. An arriving answer has
not fallen short, so it is not a Gap, and a complete answer can still carry one.
_Avoid_: Loading, pending, partial, streaming

**Origin**:
One way a Skill was delivered and set off: its Trigger, the place it was loaded from, and the Plugin
and Marketplace behind it where a plugin delivered it. A Skill name with two Origins is two Skills
sharing a name.

**Repository**:
The git repository a session ran in, named `owner/name` from its `origin` remote. A session with no
`origin` remote has no Repository, and a Filter that asks for one leaves it out.
_Avoid_: Project, folder, workspace

**Turn**:
One request to the model, the tokens it spent and what it cost. It is the unit of spend.
_Avoid_: Message, exchange, round trip

**Cost**:
What Claude Code estimates a Turn cost, at the prices it was sent with. Studio never prices a Turn
itself, so a wrong price is corrected where Claude Code takes its prices, not in Studio.
_Avoid_: Price, bill, spend total

**Each**:
The Cost of a skill's Activations divided by how many there were. A skill with no Activations has no
Each and reads **None**. A skill whose spend Claude Code will not name has none either and reads
**Not named**, because the first says the description may be broken and the second says a real cost
is hidden. A dash means there is no answer at all, so it never stands for a missing Each.
_Avoid_: Per activation, per firing

**Attribution**:
The link from a unit of spend back to the skill that caused it. A Turn is attributed to the skill
Claude Code says was in force when the request was made, so the turn that chose a skill belongs to
no skill. Studio never infers a skill Claude Code did not name.

**Unnamed spend**:
The Turns whose skill was in force but that Claude Code will not name, because the skill came from
a plugin outside Anthropic's marketplaces. It is shown as one amount of its own and never shared out
among skills. It is not the same as a Turn that belongs to no skill.
_Avoid_: Third-party, unattributed, unknown

**Model**:
Which model answered, as telemetry spells it. It is what makes two costs comparable.
_Avoid_: Engine, LLM

**Effort**:
How hard the model was asked to think on a Turn. It moves the cost without moving the Model, so it
is reported beside it.
_Avoid_: Reasoning level, thinking budget

**Filter**:
The one way every list narrows: a span of days, a Repository and a Skill. The span is counted in
whole UTC days and takes both ends in. With no span, a list covers the **lookback**, the last seven
days, and says so. A Skill that never fired belongs in the unnarrowed answer, where its zero says
the description may be broken; a filter that asks what happened in a chosen span or one Repository
leaves it out, because it did not happen there.
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
