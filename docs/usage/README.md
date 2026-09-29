# Using Skillworks

Skillworks is a Claude Code plugin that builds a spec, ticket by ticket, while nobody watches. A human
argues the design out and publishes the spec. The loop then takes each ticket in turn: it builds the
change, reviews it, runs your Suite, and pushes it to your Target branch: a branch you name, or one
branch per spec that your team reviews as one pull request. GitHub Issues is the Tracker, so the spec
and its tickets are issues any teammate can read.

Your repo tells the loop about itself through its Steering: its rules, its tracker docs, its review files
and its Suite. Setup copies a Seed of each into your repo, and your team owns them from then
on. The skills, the scripts and the hooks are the Machinery. They run from the Plugin, and no team
edits them.

## The pages

| Page | What it covers |
|---|---|
| [Setup](setup.md) | How to install the Plugin, the questions setup asks, the files it writes, how to turn the rules into tests, and what a second run does. |
| [The loop](the-loop.md) | How a design becomes code: the two kinds of Target branch, the grill, the spec, the tickets, the steps of one ticket, Landing, what happens when a step fails, the full run and the drift check. |
| [Steering](steering.md) | Each Steering file: what it does, which part of the loop reads it, whether it always loads, and what your team can change. Then what is fixed. |
| [The Suite](suite.md) | The Suite file: the checks that decide green for your repo, and how the loop runs them. |
