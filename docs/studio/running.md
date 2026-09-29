# Running Studio

The [README](../../README.md) says how to start Studio. This page holds the rest: what `aspire run`
starts, the settings, Studio on a seeded month, and a check of the Sessions list on your own data.
[Studio's telemetry](telemetry.md) says what the Telemetry switch writes.

## What `aspire run` starts

`aspire run` starts the API, the front end, an OpenTelemetry Collector, Loki and Tempo. Loki is the
Events store and Tempo is the Trace store. The Collector, Loki and Tempo run as Docker containers.

It prints the address of Aspire's own dashboard, and the front end is the `web` resource there.
Aspire runs `npm install` and `npm run dev` for the front end, and hands it the API's address, so
there is no port to look up.

## Settings

The API reads these settings. Set each one as an environment variable, or in the API's
`appsettings.json` with the `__` as a nested section.

| Setting | What it does | Default |
|---|---|---|
| `Loki__Address` | Where Studio reads the Events store. The AppHost sets it to its own Loki. | `http://localhost:3100` |
| `Loki__Tenant` | Sent as `X-Scope-OrgID`, for a Loki with several tenants. | Not sent |
| `Loki__PatienceSeconds` | How long Studio waits on Loki before it shows a Gap. | `5` |
| `Loki__ReadsAtOnce` | How many reads Studio sends Loki at once. Loki cuts each read into parts and runs sixteen parts at a time, so more reads than this wait in its queue and run out their Patience. | `4` |
| `Loki__LookbackDays` | The lookback: how many days a list covers when the Filter has no start day. | `7` |
| `Loki__MaxQueryDays` | The most days one Loki query may cover. Studio splits a longer span, because Loki refuses a range longer than 721 hours by default. | `30` |
| `Tempo__Address` | Where Studio reads the Trace store. The AppHost sets it to its own Tempo. | `http://localhost:3200` |
| `Tempo__Tenant` | Sent as `X-Scope-OrgID`, for a Tempo with several tenants. | Not sent |
| `Tempo__RequestPatienceSeconds` | How long Studio waits on one Trace store request before it shows a Gap. | `5` |
| `Tempo__SessionPatienceSeconds` | How long Studio waits on the whole read of one Session, which is hundreds of requests. | `30` |
| `Tempo__MaxSearchDays` | The most days one Trace store search may cover. The store refuses a search longer than a week by default. | `7` |
| `Tempo__MostTraces` | The most traces one search asks for. A long Session is a few hundred traces, and the store's own default of 20 would cut it short. | `1000` |
| `Tempo__MostSessions` | The most Sessions one request names. Each name makes the address longer, and the store refuses a long address. | `100` |
| `Collector__Address` | The Collector's OTLP address. Health knocks on it, and the Telemetry switch writes it as the address Claude Code sends to. | `http://localhost:4318` |
| `Collector__PatienceSeconds` | How long Health waits on the Collector before its Lamp shows it down. | `5` |
| `ClaudeSettings__Path` | The Claude Code settings file the Telemetry switch writes. | `~/.claude/settings.json` |
| `ClaudeSettings__StampPath` | Where the Telemetry switch keeps the values it replaced, so that turning it off puts them back. | `Skillworks/telemetry-switch.json` in the local app data folder |
| `Marketplace__Path` | The Marketplace folder. Studio reads the skill names of every plugin in it, so a skill with no Activations still shows, at zero. The AppHost sets it to `plugins/` in this repo. | `plugins` |

## Studio on a seeded month

To judge a page at real volume without your own telemetry, run Studio against a throwaway Loki and
Trace store. Docker must be running. Run `npm install` in `src/Skillworks.Studio.Web` once first.
Then, from the repo root:

```
node tools/seeded-studio.mjs
```

Open `http://localhost:5173/`. The tool fills a Loki container, `skillworks-seeded-loki`, on port
3101 with a made-up month of telemetry that ends now. It also writes five whole Sessions from the
last six hours, with Prompts, Tool calls, Faults, Friction, hooks and Subagents, and puts their
Spans in a Tempo container, `skillworks-seeded-tempo`, on port 3201. Between them the five Sessions
cross every Bar, and two name a model that states its window. The tool prints a link to each one.
It runs the API on port 5199. Ctrl+C stops everything and removes both containers. The AppHost's
stores are not touched.

To seed the stores and nothing else, add `--seed-only`. The containers keep running after the tool
exits. Remove them with `docker rm -f skillworks-seeded-loki skillworks-seeded-tempo`.

## Check the Sessions list on your own data

With Aspire running, this loads the Sessions list 15 times, one load after another. It counts the
loads that end in "No signal", and then reads Loki's query log to find how long the parts of those
loads waited in Loki's queue. From the repo root:

```
node tools/no-signal-check.mjs
```

It exits with 1 when a load ended in "No signal". Add `--api <address>` when the API is not on
`http://localhost:5222`, `--loads <n>` for another number of loads, and `--loki <name>` when more than
one container is named `loki-*`. The check is not in the Suite, because it needs your own data and a
running app.

The AppHost's Loki is a persistent container, and it keeps the flags it was made with. The check
stops when the container lacks a flag from `src/Skillworks.AppHost/LokiFlags.cs`, and names the
container. Stop Aspire, remove the container with `docker rm -f <name>`, and start Aspire again. The
data stays in its volume.
