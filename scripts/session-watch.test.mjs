import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

const SCRIPT = join(import.meta.dirname, "session-watch.mjs");

const REQUIRED = {
  session_id: "3f2a9c1e-5b7d-4e8f-a1c2-9d0e6b4f7a31",
  transcript_path: "/home/dev/.claude/projects/work/3f2a9c1e.jsonl",
  cwd: "/home/dev/work",
  hook_event_name: "InstructionsLoaded",
  file_path: "/home/dev/work/CLAUDE.md",
  memory_type: "Project",
  load_reason: "session_start",
};

const FULL = {
  ...REQUIRED,
  prompt_id: "b8e1d4a7-2c6f-4a9b-8e3d-1f5c7a2b9e60",
  file_path: "/home/dev/work/.claude/rules/comments.md",
  load_reason: "path_glob_match",
  globs: ["src/**/*.cs", "src/**/*.ts"],
  trigger_file_path: "/home/dev/work/src/Program.cs",
  parent_file_path: "/home/dev/work/CLAUDE.md",
};

const OPTIONAL = ["prompt_id", "globs", "trigger_file_path", "parent_file_path"];

const REASONS = ["session_start", "nested_traversal", "path_glob_match", "include", "compact"];

const OTLP_VALUES = ["stringValue", "boolValue", "intValue", "doubleValue", "arrayValue", "kvlistValue"];

let temp;

beforeEach(async () => {
  temp = await mkdtemp(join(tmpdir(), "session-watch-"));
});

afterEach(async () => {
  await rm(temp, { recursive: true, force: true });
});

async function collector() {
  const received = [];
  const server = createServer((request, response) => {
    let body = "";
    request.on("data", (chunk) => (body += chunk));
    request.on("end", () => {
      received.push({ path: request.url, type: request.headers["content-type"], body: JSON.parse(body) });
      response.writeHead(200, { "content-type": "application/json" });
      response.end("{}");
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const endpoint = `http://127.0.0.1:${server.address().port}`;
  return { endpoint, received, close: () => new Promise((resolve) => server.close(resolve)) };
}

// A port that was just let go refuses the next connection.
async function refusingEndpoint() {
  const server = createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  await new Promise((resolve) => server.close(resolve));
  return `http://127.0.0.1:${port}`;
}

function watch(payload, endpoint) {
  const env = { ...process.env };
  delete env.OTEL_EXPORTER_OTLP_ENDPOINT;
  if (endpoint !== undefined) env.OTEL_EXPORTER_OTLP_ENDPOINT = endpoint;
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [SCRIPT], { cwd: temp, env });
    let err = "";
    child.stderr.on("data", (chunk) => (err += chunk));
    child.on("error", reject);
    child.on("close", (status) => resolve({ status, err }));
    child.stdin.end(JSON.stringify(payload));
  });
}

async function recordFor(payload) {
  const store = await collector();
  try {
    const ran = await watch(payload, store.endpoint);
    assert.equal(ran.status, 0, ran.err);
    assert.equal(store.received.length, 1);
    return store.received[0];
  } finally {
    await store.close();
  }
}

function onlyRecord(request) {
  const records = request.body.resourceLogs.flatMap((r) => r.scopeLogs.flatMap((s) => s.logRecords));
  assert.equal(records.length, 1);
  return records[0];
}

function attributes(record) {
  return Object.fromEntries(record.attributes.map(({ key, value }) => [key, plain(value)]));
}

function plain(value) {
  if ("stringValue" in value) return value.stringValue;
  if ("arrayValue" in value) return value.arrayValue.values.map(plain);
  throw new Error(`an attribute value this test does not read: ${JSON.stringify(value)}`);
}

function assertAnyValue(value) {
  const kinds = Object.keys(value);
  assert.equal(kinds.length, 1, `one kind of value, not ${JSON.stringify(value)}`);
  assert.ok(OTLP_VALUES.includes(kinds[0]), `an OTLP value kind, not ${kinds[0]}`);
  if (kinds[0] === "arrayValue") value.arrayValue.values.forEach(assertAnyValue);
}

test("a Load arrives as one record carrying every field of the payload", async () => {
  // Act
  const record = onlyRecord(await recordFor(FULL));

  // Assert
  const got = attributes(record);
  for (const [key, value] of Object.entries(FULL)) assert.deepEqual(got[key], value, key);
  assert.equal(got["event.name"], "instructions_loaded");
  assert.equal(got["session.id"], FULL.session_id);
  assert.equal(got["prompt.id"], FULL.prompt_id);
  assert.equal(record.body.stringValue, "claude_code.instructions_loaded");
  assert.equal(record.severityText, "INFO");
});

test("a payload with only the required fields leaves the optional attributes absent", async () => {
  // Act
  const record = onlyRecord(await recordFor(REQUIRED));

  // Assert
  const keys = record.attributes.map((a) => a.key);
  for (const key of [...OPTIONAL, "prompt.id"]) assert.ok(!keys.includes(key), `${key} is absent`);
  for (const { key, value } of record.attributes) assert.notEqual(plain(value), "", `${key} is not empty`);
  for (const key of Object.keys(REQUIRED)) assert.ok(keys.includes(key), `${key} is present`);
});

for (const reason of REASONS) {
  test(`the load reason ${reason} reaches the record unchanged`, async () => {
    // Act
    const record = onlyRecord(await recordFor({ ...REQUIRED, load_reason: reason }));

    // Assert
    assert.equal(attributes(record).load_reason, reason);
  });
}

test("the stamp is a decimal string of nanoseconds", async () => {
  // Arrange
  const before = BigInt(Date.now()) * 1_000_000n;

  // Act
  const record = onlyRecord(await recordFor(REQUIRED));

  // Assert
  assert.equal(typeof record.timeUnixNano, "string");
  assert.match(record.timeUnixNano, /^[0-9]+$/);
  assert.ok(BigInt(record.timeUnixNano) >= before);
});

test("the record is OTLP JSON posted where the Collector takes logs", async () => {
  // Act
  const request = await recordFor(FULL);

  // Assert
  assert.equal(request.path, "/v1/logs");
  assert.match(request.type, /^application\/json/);
  onlyRecord(request);
  for (const resource of request.body.resourceLogs) {
    for (const { key, value } of resource.resource.attributes) {
      assert.equal(typeof key, "string");
      assertAnyValue(value);
    }
    for (const scope of resource.scopeLogs) {
      assert.equal(typeof scope.scope.name, "string");
      for (const record of scope.logRecords) {
        assert.match(record.timeUnixNano, /^[0-9]+$/);
        assert.equal(record.severityNumber, 9);
        assertAnyValue(record.body);
        for (const { key, value } of record.attributes) {
          assert.equal(typeof key, "string");
          assertAnyValue(value);
        }
      }
    }
  }
});

test("an unset endpoint exits zero without an error", async () => {
  // Act
  const ran = await watch(FULL, undefined);

  // Assert
  assert.equal(ran.status, 0);
  assert.equal(ran.err, "");
});

test("a refused connection exits zero without an error", async () => {
  // Arrange
  const endpoint = await refusingEndpoint();

  // Act
  const ran = await watch(FULL, endpoint);

  // Assert
  assert.equal(ran.status, 0);
  assert.equal(ran.err, "");
});
