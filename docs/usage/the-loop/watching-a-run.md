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

A card shows:

- The spec, and what the loop does now: cutting tickets, building tickets, the full run, the drift
  check, the Name check, finished, stopped or gone. Between tickets, a line under it says what that
  part of the loop does.
- The time left, when the driver knows it, and the counts of Choices and Denials so far.
- Each ticket of the spec. `✓ Landed` is a ticket that Landed, `▶ now` is the ticket the loop builds
  now, and `· to come` is a ticket still to come.
- The steps of the current ticket. `✓` is a step that is done, `▶` is the step the loop is on, and
  `○` is a step still to come. The time the step has run shows beside `▶`, and a line under it says
  what the step does.

```
Spec #589 · building tickets
~1h 5m left · 2 Choices · 1 Denial
✓ Landed  #590 TICKET: The driver writes a Position
▶ now     #592 TICKET: A pane shows every running loop
· to come #593 TICKET: Clear a loop that ended
Ticket 2 of 3: #592
✓ build
▶ review: standards  4m in step
  Reviews the change against your rules. Fixes what it can, and reports the rest.
○ review: spec
○ rebase, verify, and push
```

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
