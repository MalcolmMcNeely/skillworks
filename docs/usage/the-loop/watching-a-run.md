# Watching a run

Part of [the Dev loop](../the-loop.md).

The Plugin ships a mod. A mod is a part of the Plugin that draws in Claude Code's own window. It
shows a pane beside the chat, and the pane shows every loop that runs in your clone. A loop you
started in another terminal shows there too.

## What the pane shows

The pane draws each loop as a card. A card has a border, and the colour of the border says the
state of the loop:

| Border | State |
|---|---|
| yellow | running |
| green | finished |
| red | stopped |
| grey | gone |

The cards stack. Running cards come first, then cards of loops that ended. In each group the newest
comes first: a running loop by when its run started, and a loop that ended by when it ended.

A running card shows, from the top:

- The spec, and what the loop does now: cutting tickets, building tickets, the full run, the drift
  check, the Name check, finished, stopped or gone. Between tickets, a line under it says what that
  part of the loop does.
- A progress bar for the whole path of the spec, and a line of text under it, such as
  `64% · tickets 4/4 · checks 1/4 · full run to come`. Progress below says how it counts.
- The path row, a row of chips for the whole path of the spec. Progress below says what each chip
  shows.
- The current ticket, and under it the step strip: one chip for each step of the ticket, from
  `build` to `land`. `✓` is a step that is done, a spinner such as `⠋` is the step the loop is on
  now, and `○` is a step still to come.
- The time in the step, which is how long the step now has run, and under it a line that says what
  the step does.
- The time left, when the driver knows it, and the counts of Choices and Denials so far.
- The ticket list, in two parts. First come the spec's own tickets. Then come the line `Filed by the
  checks` and the tickets a judge filed. `✓ Landed` is a ticket that Landed, `▶ now` is the ticket
  the loop builds now, and `· to come` is a ticket still to come.

A card of a loop that ended shows no bar, no path row and no step strip.

```
Spec #589 · building tickets
███████████░░░░░░░░░
56% · tickets 3/3 · checks 2/4 · full run to come
✓ tickets 3/3  ✓ deepen · 1 Strong → 1 ticket  ✓ simplify · 0 findings
○ drift  ○ names  ○ full run
Ticket 4 of 4: #601
✓ build  ✓ review: standards  ⠋ review: spec  ○ rebase, verify, and push
4m in step
  Reviews the change against the ticket and the spec. Fixes what it can, and reports the rest.
~1h 5m left · 2 Choices · 1 Denial
✓ Landed  #590 TICKET: The driver writes a Position
✓ Landed  #592 TICKET: A pane shows every running loop
✓ Landed  #593 TICKET: Clear a loop that ended
Filed by the checks
▶ now     #601 TICKET: Deepen the Position  ◆ deepen
```

Each ticket a judge filed carries a tag: a diamond, `◆`, and the judge's short name, such as
`◆ deepen`. The tag is drawn in the judge's own colour, so you see at a glance which judge asked for
the ticket:

| Tag | Judge | Colour |
|---|---|---|
| `◆ deepen` | the Deepening check | magenta |
| `◆ simplify` | the Simplify check | cyan |
| `◆ drift` | the drift check | blue |
| `◆ names` | the Name check | white |

A ticket a judge filed shows only once the Position holds it, which is when the judge has filed it on
the Tracker. When no judge filed a ticket, the card has no `Filed by the checks` line.

The pane names a step for someone who has not read these pages. The log and the Position use the
step's own name, as [the steps of one ticket](steps.md) lists them:

| In the log | In the pane |
|---|---|
| `build` | build |
| `standards` | review: standards |
| `spec` | review: spec |
| `architecture` | review: architecture |
| `fix` | review fixes |
| `sweep` | comment sweep |
| `suite` | suite |
| `finish` | close ticket and commit |
| `land` | rebase, verify, and push |

The pieces of a run beyond the steps of one ticket have names of their own too. The path row uses
the short name:

| In the log | In the pane |
|---|---|
| `baseline` | the baseline, which runs before the first ticket |
| `cut` | cutting tickets |
| `deepening-check` | the Deepening check, `deepen` in the path row |
| `simplify-check` | the Simplify check, `simplify` in the path row |
| `drift-check` | the drift check, `drift` in the path row |
| `name-check` | the Name check, `names` in the path row |
| `full-run` | the full run, `full run` in the path row |

## Progress

The progress bar counts the whole path of the spec, and not only its tickets. So a card does not
say done while the judges and the full run still have to run. The judges are the four checks at the
end of a spec: the Deepening check, the Simplify check, the drift check and the Name check.

The bar counts one share for each of the spec's own tickets, one for each judge that is not off, and
one for the full run. A ticket fills its share when it Lands. A judge that filed no ticket fills its
share when it is done. A judge that filed tickets fills half its share when it is done, and its own
tickets fill the second half as they Land. The full run fills its share when it is done.

A ticket a judge files adds no share, so the bar never moves back when a judge files one.

The text under the bar says the percentage, how many of the spec's own tickets Landed, how many of
the judges that are not off are done, and where the full run is: `64% · tickets 4/4 · checks 1/4 ·
full run to come`.

The path row has one chip for the spec's own tickets, one for each judge in the order the loop runs
them, and one for the full run. The tickets chip shows how many Landed over how many there are, such
as `tickets 2/3`. Each chip has a mark:

| Mark | The piece |
|---|---|
| `✓` | done |
| a spinner, such as `⠋` | runs now |
| `○` | to come |
| `✕` | off |

An off chip is drawn crossed out. Your team turned that judge off in its Steering file, so do not
wait for it. When a judge is done, its chip adds what it found and the tickets it filed, such as
`deepen · 2 Strong → 2 tickets`. Each judge counts in its own word: Strong for the Deepening check,
findings for the Simplify check, Gaps for the drift check and renames for the Name check.

The pane reads the Position, `.spec-loop/<spec>/position.json`, and the Step times,
`.spec-loop/<spec>/step-times.jsonl`, every few seconds. It never reads `loop.log`, and it shows no
log lines. [Reading a run](reading-a-run.md) says what the log and the Step times hold.

A loop folder whose Position has no judges, or that has no Step times, is a run from a Plugin older
than this pane. The pane shows no card for it. A new run shows its card once its first piece, the
baseline, has ended, because that is when the driver writes its first Step time.

## Finished, stopped and gone

A loop that is **finished** reached its end, and every ticket is on the Target branch. Its card says
`finished`.

A loop that is **stopped** ended early. Its card says `stopped`, and shows the stop line and the path
to the log, such as `Log: .spec-loop/589/loop.log`. [When a step fails](stops.md) says what each stop
line means and how to restart.

A loop that is **gone** has a driver that died before it could write its end. The driver writes a
heartbeat time into the Position every 30 seconds while it runs. When that time is more than 2
minutes old, and the loop is not finished or stopped, its card says `gone`. Read `loop.log` to see
the last step it reached.

## Clear

A loop that ended, as finished, stopped or gone, stays in the pane until you clear it. So you do not
miss a stop while you are away. Its card has a `Clear` button, and a card of a running loop has
none.

Press `Clear` to take the card out of the pane. The mod keeps the clear against that run of the
driver, so the same run does not come back in your next Session. When you start that spec again, the
new run shows in the pane.

## When the pane opens

The pane opens by itself when a loop starts a run that this Session has not seen before. When you
close the pane, it stays closed until a new run starts.

A pane that opens by itself waits for room. In a narrow terminal it does not open beside the chat.
It shows when you widen the terminal, or when you open it yourself.

To open the pane yourself, type:

```
/loop-view
```

## When nothing shows

The mod does nothing when no loop has a Position in your clone. It does nothing in a headless
Session either, such as a step Session that the driver starts. It opens nothing, reads nothing and
writes nothing there.

When an admin blocks mods, the pane does not show. The skills of the Plugin still work.
