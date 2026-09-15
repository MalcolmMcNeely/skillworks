# At-a-glance Home

A prototype, kept as a record. It asked: what should Home look like, so the telemetry reads at a
glance with no page of words to get through?

Five variants of Home: A Deck, B Scope, C Pulse, D Spend and E Map. The verdict was E. It takes D's
instrument rail and treemap in A's colours, with A's activity strip across the top.

The web app never builds, lints or tests this folder, but the architecture check still scans it. Its
imports point at code in the web app that may no longer exist. To see the variants run, check out commit `918636a`, run
`node scripts/prototype-glance.mjs` and open `http://localhost:5173/?variant=E`.
