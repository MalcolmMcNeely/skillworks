# Using Skillworks

Skillworks is a Claude Code plugin that builds a spec, ticket by ticket, while nobody watches. A human
argues the design out and publishes the spec. The loop then takes each ticket in turn: it builds the
change, reviews it, runs your Suite, and pushes it to `main`. GitHub Issues is the Tracker, so the
spec and its tickets are issues any teammate can read.

Your repo tells the loop about itself through its Steering: its rules, its tracker docs, its review
baselines and its Suite. Setup copies a Seed of each into your repo, and your team owns them from then
on. The skills, the scripts and the hooks are the Machinery. They run from the Plugin, and no team
edits them.

## The pages

| Page | What it covers |
|---|---|
| [The loop](the-loop.md) | How a design becomes code: the grill, the spec, the tickets, the steps of one ticket, Landing, what happens when a step fails, the full run and the drift check. |
| [The Suite](suite.md) | The Suite file: the checks that decide green for your repo, and how the loop runs them. |
