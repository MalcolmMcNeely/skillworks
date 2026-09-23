// The record copies the shape of Claude Code's own events, so one Loki query reads both.

import { execFile } from "node:child_process";
import { text } from "node:stream/consumers";
import { promisify } from "node:util";

const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT;

// A Session's first answer waits on this hook, so a slow git or a silent Collector must not hold it to the hook limit.
const HOOK_LIMIT_MS = 1000;

// Claude Code's own events carry this key from OTEL_RESOURCE_ATTRIBUTES, so the hook's records must too, or a Child reaches the Sessions list alone.
const PARENT_KEY = "skillworks.parent.session.id";

// A machine with no Collector is not served, so it pays nothing, not even a socket.
if (!endpoint) process.exit(0);

const limit = AbortSignal.timeout(HOOK_LIMIT_MS);

try {
  const payload = JSON.parse(await text(process.stdin));
  const repository = await repositoryOf(payload.cwd);
  await fetch(new URL("v1/logs", endpoint.endsWith("/") ? endpoint : `${endpoint}/`), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(recordOf(payload, repository)),
    signal: limit,
  });
} catch {
  // Silent and exit zero on purpose: a hook must never interrupt a Session for a store that is down.
}

async function repositoryOf(cwd) {
  if (!["1", "true"].includes(process.env.OTEL_METRICS_INCLUDE_REPOSITORY?.toLowerCase())) return {};
  try {
    const { stdout } = await promisify(execFile)("git", ["-C", cwd ?? process.cwd(), "remote", "get-url", "origin"], {
      signal: limit,
    });
    const [owner, name] = stdout.trim().replace(/\.git$/, "").split(/[/:]/).slice(-2);
    return owner && name ? { owner, name } : {};
  } catch {
    // A Repository that cannot be read must not stop the record going.
    return {};
  }
}

function recordOf(payload, repository) {
  const event = snakeCase(payload.hook_event_name);
  const attributes = [
    attribute("event.name", event),
    attribute("session.id", payload.session_id),
    attribute(PARENT_KEY, resourceAttribute(PARENT_KEY)),
    attribute("prompt.id", payload.prompt_id),
    attribute("vcs.owner.name", repository.owner),
    attribute("vcs.repository.name", repository.name),
    ...Object.entries(payload).map(([key, value]) => attribute(key, value)),
  ].filter(Boolean);

  return {
    resourceLogs: [
      {
        resource: { attributes: [attribute("service.name", "claude-code")] },
        scopeLogs: [
          {
            // Studio's events reader leaves this scope out, so a record never passes for Claude Code's own event.
            scope: { name: "skillworks.session-watch" },
            logRecords: [
              {
                // OTLP JSON sends 64-bit integers as decimal strings, and rejects a number.
                timeUnixNano: (BigInt(Date.now()) * 1_000_000n).toString(),
                severityNumber: 9,
                severityText: "INFO",
                body: { stringValue: `claude_code.${event}` },
                attributes,
              },
            ],
          },
        ],
      },
    ],
  };
}

function resourceAttribute(key) {
  for (const pair of (process.env.OTEL_RESOURCE_ATTRIBUTES ?? "").split(",")) {
    const [name, ...value] = pair.split("=");
    if (name.trim() === key) return value.join("=").trim() || undefined;
  }
  return undefined;
}

function attribute(key, value) {
  const encoded = valueOf(value);
  return encoded === undefined ? undefined : { key, value: encoded };
}

function valueOf(value) {
  if (value === undefined || value === null) return undefined;
  if (typeof value === "string") return { stringValue: value };
  if (typeof value === "boolean") return { boolValue: value };
  if (typeof value === "number") {
    return Number.isInteger(value) ? { intValue: String(value) } : { doubleValue: value };
  }
  if (Array.isArray(value)) {
    return { arrayValue: { values: value.map(valueOf).filter(Boolean) } };
  }
  return {
    kvlistValue: { values: Object.entries(value).map(([key, inner]) => attribute(key, inner)).filter(Boolean) },
  };
}

function snakeCase(name) {
  return String(name).replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
}
