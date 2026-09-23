// The record copies the shape of Claude Code's own events, so one Loki query reads both.

import { text } from "node:stream/consumers";

const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT;

// A machine with no Collector is not served, so it pays nothing, not even a socket.
if (!endpoint) process.exit(0);

try {
  const payload = JSON.parse(await text(process.stdin));
  await fetch(new URL("v1/logs", endpoint.endsWith("/") ? endpoint : `${endpoint}/`), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(recordOf(payload)),
  });
} catch {
  // Silent and exit zero on purpose: a hook must never interrupt a Session for a store that is down.
}

function recordOf(payload) {
  const event = snakeCase(payload.hook_event_name);
  const attributes = [
    attribute("event.name", event),
    attribute("session.id", payload.session_id),
    attribute("prompt.id", payload.prompt_id),
    ...Object.entries(payload).map(([key, value]) => attribute(key, value)),
  ].filter(Boolean);

  return {
    resourceLogs: [
      {
        resource: { attributes: [attribute("service.name", "claude-code")] },
        scopeLogs: [
          {
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
