# Session views

A prototype, kept as a record. It asked: how does a single Claude Code session read, once you have
every event and every span it produced?

Four variants: A Drill, Miller columns over a scrolling dashboard; B Scrub, one timeline instrument
with a brush that every other panel follows; C Story, an index table then the conversation as
chapters; D Duo. The verdict was D. It takes C's index table as the way in and B's instrument as the
session itself.

All four share one session model, one seeded fixture of 97 sessions and one set of derivations, so
the figures agree when a reader flips between them. The fixture's durations, token counts, hook costs
and failure rates follow Loki data measured on 2026-09-15. Its words are invented.

The web app never builds, lints or tests this folder, but the architecture check still scans it. Its
imports point at code in the web app that may no longer exist. To see the variants run, check out
branch `prototype/session-views`, run `node scripts/prototype-sessions.mjs` and open
`http://localhost:5180/prototype/sessions`.

## What it got wrong

Two faults were found after the verdict, by testing telemetry rather than reading the docs.

The model groups a subagent's work by `prompt_id`. That does not hold: `prompt_id` follows the main
thread and changes part way through a subagent's run if a person types while it works. A subagent's
work is found through its spans, which carry an id of their own.

The model assumes a span carries the text of a subagent's instruction and its report. No span carries
either. The report is in the subagent's own `assistant_response` event, and the instruction survives
only as its first 128 characters.
