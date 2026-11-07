# Watching a run

Part of [the Dev loop](../the-loop.md).

The Plugin ships a mod. A mod is a part of the Plugin that draws in Claude Code's own window. It
shows a pane beside the chat, and the pane shows every loop that runs in your clone. A loop you
started in another terminal shows there too.

## What the pane shows

The pane has one block for each loop. A block shows:

- The spec, and what the loop does now: cutting tickets, building tickets, the full run, the drift
  check, the Name check, finished or stopped.
- The time left, when the driver knows it, and the counts of Choices and Denials so far.
- Each ticket of the spec. `✓` is a ticket that Landed, `▶` is the ticket the loop builds now, and
  `·` is a ticket still to come.
- The steps of the current ticket. `✓` is a step that is done, `▶` is the step the loop is on, and
  `○` is a step still to come. The time the step has run shows beside `▶`.

```
Spec #589 · building tickets
~1h 5m left · 2 Choices · 1 Denials
✓ #590 TICKET: The driver writes a Position
▶ #592 TICKET: A pane shows every running loop
· #593 TICKET: Clear a loop that ended
#592, ticket 2 of 3
✓ build
▶ standards  4m in step
○ spec
○ land
```

The pane reads the Position, `.spec-loop/<spec>/position.json`, every few seconds. It never reads
`loop.log`, and it shows no log lines. [Reading a run](reading-a-run.md) says what the log holds.

## Finished and stopped

A loop that is **finished** reached its end, and every ticket is on the Target branch. Its block says
`finished`.

A loop that is **stopped** ended early. Its block says `stopped`, and shows the stop line and the path
to the log, such as `Log: .spec-loop/589/loop.log`. [When a step fails](stops.md) says what each stop
line means and how to restart.

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
