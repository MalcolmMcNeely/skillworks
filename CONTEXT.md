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
organisation's stores, never from the machine it runs on.
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
Publish, and one for Sessions, and leads to the ones that are built.
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
on. With the Trace store it is one of the two places Studio reads what it measures. Studio keeps
nothing of its own.
_Avoid_: Event log, telemetry store, transcript store, database

**Activation**:
One occasion on which a skill fired. It holds only what Claude Code said when the skill fired: the
skill, the time and its Origin, with its Session and its Repository where those are not already
known. A list of one Session's Activations knows both, so it keeps how long the skill ran instead.
_Avoid_: Invocation, call, skill call, firing, run, usage

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
the developer to do. Whether telemetry is switched on is read from the machine Studio runs on, so
that Gap speaks for this machine only. A period a store holds nothing for is labelled missing, never
shown as none. A store that stops answering part way keeps the days already read, and the Gap names
the days it could not read. The Events store and the Trace store answer on their own, so a Gap names
which of them fell short.
_Avoid_: Error, empty, null

**Arriving**:
An answer from a store that has not finished reaching the screen. What has landed is shown at once,
and its figures can still grow. It is **complete** when its last part lands. An arriving answer has
not fallen short, so it is not a Gap, and a complete answer can still carry one. A Session arrives
in two parts, its events and then its Spans, so its Depth can grow from Thin to Full as a reader
looks at it.
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
_Avoid_: Message, round trip

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
The one way every list narrows: a span of days, a Repository, a Skill and a Depth. The span is
counted in whole UTC days and takes both ends in. With no span, a list covers the **lookback**, the
last seven days, and says so. A Skill that never fired belongs in the unnarrowed answer, where its
zero says the description may be broken; a filter that asks what happened in a chosen span or one
Repository leaves it out, because it did not happen there.
_Avoid_: Query, search, scope

**Activation eval**:
A test of whether a skill activates on the prompts it should, and stays quiet on the ones it should
not. Cheap. Applies to every engine.
_Avoid_: Firing eval, trigger test, discovery eval

**Outcome eval**:
A test of whether a skill's output meets its contract once it has fired. Expensive. Applies only
where a skill promises something observable.
_Avoid_: Quality eval, judge eval

**Contract**:
The part of a skill's output that can be asserted without a model judging it.

### Sessions

**Session**:
One run of Claude Code, in one Repository, by one person. No event says a Session ended, so a
Session is **Running** while its last event is recent and never again after that. Its name is the
title Claude Code wrote for it, and the first Prompt where it wrote none.
_Avoid_: Conversation, thread, transcript

**Prompt**:
The words a person typed, and nothing that followed them.
_Avoid_: Message, instruction, query

**Exchange**:
One Prompt and everything that followed it, up to the answer. It is the band on a timeline and the
block in a conversation, and many Turns sit inside one.
_Avoid_: Round trip, interaction, cycle

**Step**:
One thing in a Session that took time: a Turn, a Tool call, a hook run or a Subagent. Every Step has
a start and an end.
_Avoid_: Event, entry, item

**Tool call**:
One use of one tool by one agent.

**Main agent**:
The agent Claude Code runs a Session as. Every Step no Subagent ran belongs to it.
_Avoid_: Main thread, root agent, parent agent

**Subagent**:
An agent the main agent started. It has its own brief, its own Turns and its own Tool calls, and a
reader opens it the way they open a Session. Only the opening words of its brief survive, with the
length of the rest, so a Subagent is named by the description its caller gave it.
_Avoid_: Sub-task, worker, child agent

**Fault**:
A Tool call that failed, or a model error. Nobody chose it, and that is what makes it worth
counting.
_Avoid_: Error, failure, problem

**Friction**:
A Tool call a person refused, or one a hook blocked. Somebody chose it, so it is counted apart from
Faults and never added to them.
_Avoid_: Block, rejection, denial

**Finding**:
Something Studio names in a Session because it crossed a bar worth a person's attention. Every
Finding shows the figure it crossed on, so a reader sees how close the call was. Clicking a Finding
moves the reader to the moment it happened. A Finding that needs the Trace store reads **not known**
in a Thin Session, never zero.
_Avoid_: Insight, issue, alert

**Bar**:
The figure a Session has to pass before Studio names a Finding. Every bar is in one table, so what
counts as worth a person's attention is tuned in one place. A bar that was measured and not crossed
comes back as no Finding at all, and a bar only a Span could measure comes back with no figure.
_Avoid_: Threshold, limit, rule

**Trace**:
One Session as the Trace store holds it: its Spans, and the tree they make. The Trace panel draws
that tree.

**Trace store**:
The organisation's store that Claude Code's Spans arrive in, once traces are switched on. It answers
apart from the Events store, and it falls short apart from it.
_Avoid_: Tempo, span store, tracing backend

**Span**:
One Step as the Trace store holds it, with the Steps that ran inside it. A Span says what an event
cannot: which Subagent ran a Tool call, how long it waited for a person's permission, and what came
back.

**Depth**:
How much of a Session can be read: **Full** when its Spans and its words are both there, and
**Thin** when they are not. It is part of the Filter, so a reader asks for what they can read
instead of opening Sessions to find out.
_Avoid_: Fidelity, completeness, quality

**Split**:
Where a Session's time went, as eight Parts that hold no moment twice and add up to its length:
your turn, nothing running, model thinking, tools running, waiting for your OK, hooks, only
subagents and side requests. Each Part is also reported with its overlaps, so a reader sees both
what a Part took on its own and what it took in all.
_Avoid_: Breakdown, time analysis, profile

**Part**:
One of the eight things a moment of a Session can be spent on. A moment belongs to exactly one
Part, so the busiest Part that was running takes it. Waiting for your OK, hooks and only subagents
each need a Span, and all three read **not known** in a Thin Session, never zero.
_Avoid_: Bucket, category, slice

**Spell**:
One bounded piece of a Session's time: a start and a length. What filled it is said beside it, a
Part or a Subagent, and a Spell with nothing beside it is only the piece of time. A View is applied
by clipping each Spell to it, so every figure beneath the timeline narrows without asking a store
again.
_Avoid_: Stint, stretch, interval, segment, block

**View**:
The part of a run a reader dragged over on the timeline. Every panel reads the View alone, so its
figures answer the question the reader asked and no other. With no View, every panel reads the whole
run. A reader meets it as **in view** and never by name, so nobody has to learn a word to read a
figure.
_Avoid_: Brush, stretch, range, selection, window
