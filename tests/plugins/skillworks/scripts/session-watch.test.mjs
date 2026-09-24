import { execFileSync, spawn } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { createServer } from "node:http";
import { createServer as createSocketServer } from "node:net";
import { platform, tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

const ROOT = join(import.meta.dirname, "..", "..", "..", "..");

const PLUGIN = join(ROOT, "plugins", "skillworks");

const SCRIPT = join(PLUGIN, "scripts", "session-watch.mjs");

const HOOKED = ["InstructionsLoaded", "SessionStart"];

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

const SESSION = {
  session_id: REQUIRED.session_id,
  transcript_path: REQUIRED.transcript_path,
  cwd: REQUIRED.cwd,
  hook_event_name: "SessionStart",
  source: "startup",
  model: "claude-opus-5-5",
};

const EVENTS = [["a Load", FULL], ["a Session", SESSION]];

const SOURCES = ["startup", "resume", "clear", "compact", "fork"];

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

async function silentEndpoint() {
  const sockets = new Set();
  let accepted = 0;
  const server = createSocketServer((socket) => {
    accepted += 1;
    sockets.add(socket);
    socket.on("error", () => {});
    socket.on("close", () => sockets.delete(socket));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const endpoint = `http://127.0.0.1:${server.address().port}`;
  const close = () => {
    for (const socket of sockets) socket.destroy();
    return new Promise((resolve) => server.close(resolve));
  };
  return { endpoint, accepted: () => accepted, close };
}

// Git reads its global config before anything else, so a config that never finishes arriving holds every git call.
async function endlessGitConfig() {
  if (platform() !== "win32") {
    const fifo = join(temp, "endless-config");
    execFileSync("mkfifo", [fifo]);
    return { path: fifo, close: async () => {} };
  }
  const pipe = `\\\\.\\pipe\\session-watch-${process.pid}-${Math.random().toString(36).slice(2)}`;
  const sockets = new Set();
  const server = createSocketServer((socket) => {
    sockets.add(socket);
    socket.on("error", () => {});
  });
  await new Promise((resolve) => server.listen(pipe, resolve));
  const close = () => {
    for (const socket of sockets) socket.destroy();
    return new Promise((resolve) => server.close(resolve));
  };
  return { path: pipe, close };
}

async function pluginHooks() {
  return JSON.parse(await readFile(join(PLUGIN, "hooks", "hooks.json"), "utf8")).hooks;
}

async function hookLimits() {
  return Object.fromEntries(
    Object.entries(await pluginHooks()).map(([event, groups]) => [event, groups[0].hooks[0].timeout * 1000]),
  );
}

async function repository(origin) {
  const dir = await mkdtemp(join(temp, "repository-"));
  execFileSync("git", ["init", "--quiet", dir]);
  if (origin !== undefined) execFileSync("git", ["-C", dir, "remote", "add", "origin", origin]);
  return dir;
}

function watch(payload, endpoint, extra = {}, signal) {
  const env = { ...process.env };
  delete env.OTEL_EXPORTER_OTLP_ENDPOINT;
  delete env.OTEL_METRICS_INCLUDE_REPOSITORY;
  delete env.OTEL_RESOURCE_ATTRIBUTES;
  if (endpoint !== undefined) env.OTEL_EXPORTER_OTLP_ENDPOINT = endpoint;
  Object.assign(env, extra);
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [SCRIPT], { cwd: temp, env, signal });
    let err = "";
    child.stderr.on("data", (chunk) => (err += chunk));
    child.on("error", (error) => (error.name === "AbortError" ? undefined : reject(error)));
    child.on("close", (status) => resolve({ status, err }));
    child.stdin.end(JSON.stringify(payload));
  });
}

async function recordFor(payload, extra) {
  const store = await collector();
  try {
    const ran = await watch(payload, store.endpoint, extra);
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

for (const [name, payload] of EVENTS) {
  test(`${name} is sent under the scope Studio leaves out of Claude Code's events`, async () => {
    // Act
    const request = await recordFor(payload);

    // Assert
    const scopes = request.body.resourceLogs.flatMap((resource) => resource.scopeLogs.map((scope) => scope.scope.name));
    assert.deepEqual(scopes, ["skillworks.session-watch"]);
  });

  test(`${name} with the endpoint unset sends nothing and exits zero`, async () => {
    // Arrange
    const store = await collector();

    try {
      // Act
      const ran = await watch(payload, undefined);

      // Assert
      assert.equal(ran.status, 0);
      assert.equal(ran.err, "");
      assert.equal(store.received.length, 0);
    } finally {
      await store.close();
    }
  });

  test(`${name} whose connection is refused exits zero without an error`, async () => {
    // Arrange
    const endpoint = await refusingEndpoint();

    // Act
    const ran = await watch(payload, endpoint);

    // Assert
    assert.equal(ran.status, 0);
    assert.equal(ran.err, "");
  });
}

for (const event of HOOKED) {
  test(`the Plugin runs this script on ${event} from the Plugin root`, async () => {
    // Act
    const groups = (await pluginHooks())[event];

    // Assert
    assert.equal(groups.length, 1);
    const [hook] = groups[0].hooks;
    assert.equal(hook.type, "command");
    assert.equal(hook.command, "node");
    assert.deepEqual(hook.args, ["${CLAUDE_PLUGIN_ROOT}/scripts/session-watch.mjs"]);
  });
}

test("the project settings register no hook of their own", async () => {
  // Act
  const settings = JSON.parse(await readFile(join(ROOT, ".claude", "settings.json"), "utf8"));

  // Assert
  assert.equal(settings.hooks, undefined);
});

const LIMITS = await hookLimits();

for (const [name, payload] of EVENTS) {
  const limit = LIMITS[payload.hook_event_name];

  test(`${name} whose Collector never answers exits zero well inside the hook limit`, { timeout: limit }, async (t) => {
    // Arrange
    const store = await silentEndpoint();

    try {
      // Act
      const started = performance.now();
      const ran = await watch(payload, store.endpoint, {}, t.signal);
      const spent = performance.now() - started;

      // Assert
      assert.ok(store.accepted() > 0, "the Collector took the connection");
      assert.equal(ran.status, 0);
      assert.equal(ran.err, "");
      assert.ok(spent < limit / 2, `ended after ${Math.round(spent)} ms, against a hook limit of ${limit} ms`);
    } finally {
      await store.close();
    }
  });
}

for (const [name, payload] of EVENTS) {
  const limit = LIMITS[payload.hook_event_name];

  test(`${name} with the Repository switch on whose Collector never answers exits zero well inside the hook limit`, { timeout: limit }, async (t) => {
    // Arrange
    const store = await silentEndpoint();
    const cwd = await repository(ORIGINS[0]);

    try {
      // Act
      const started = performance.now();
      const ran = await watch({ ...payload, cwd }, store.endpoint, REPOSITORY_ON, t.signal);
      const spent = performance.now() - started;

      // Assert
      assert.ok(store.accepted() > 0, "the Collector took the connection");
      assert.equal(ran.status, 0);
      assert.equal(ran.err, "");
      assert.ok(spent < limit / 2, `ended after ${Math.round(spent)} ms, against a hook limit of ${limit} ms`);
    } finally {
      await store.close();
    }
  });

  test(`${name} whose Repository lookup never ends exits zero well inside the hook limit`, { timeout: limit }, async (t) => {
    // Arrange
    const store = await collector();
    const config = await endlessGitConfig();
    const cwd = await repository(ORIGINS[0]);

    try {
      // Act
      const started = performance.now();
      const ran = await watch({ ...payload, cwd }, store.endpoint, { ...REPOSITORY_ON, GIT_CONFIG_GLOBAL: config.path }, t.signal);
      const spent = performance.now() - started;

      // Assert
      assert.equal(ran.status, 0);
      assert.equal(ran.err, "");
      assert.ok(spent < limit / 2, `ended after ${Math.round(spent)} ms, against a hook limit of ${limit} ms`);
      assert.equal(store.received.length, 0);
    } finally {
      await config.close();
      await store.close();
    }
  });
}

test("a Session arrives as one record carrying how it began", async () => {
  // Act
  const record = onlyRecord(await recordFor(SESSION));

  // Assert
  const got = attributes(record);
  for (const [key, value] of Object.entries(SESSION)) assert.deepEqual(got[key], value, key);
  assert.equal(got["event.name"], "session_start");
  assert.equal(got["session.id"], SESSION.session_id);
  assert.equal(record.body.stringValue, "claude_code.session_start");
  assert.equal(record.severityText, "INFO");
});

for (const source of SOURCES) {
  test(`a Session begun by ${source} says so unchanged`, async () => {
    // Act
    const record = onlyRecord(await recordFor({ ...SESSION, source }));

    // Assert
    assert.equal(attributes(record).source, source);
  });
}

test("a Session is recorded when no Load follows it", async () => {
  // Arrange
  const store = await collector();

  try {
    // Act
    const ran = await watch(SESSION, store.endpoint);

    // Assert
    assert.equal(ran.status, 0, ran.err);
    const records = store.received.map(onlyRecord);
    assert.deepEqual(
      records.map((r) => r.body.stringValue),
      ["claude_code.session_start"],
    );
  } finally {
    await store.close();
  }
});

test("a Session and a Load from it carry the same session.id", async () => {
  // Arrange
  const store = await collector();

  try {
    // Act
    const session = await watch(SESSION, store.endpoint);
    const load = await watch(REQUIRED, store.endpoint);

    // Assert
    assert.equal(session.status, 0, session.err);
    assert.equal(load.status, 0, load.err);
    const records = store.received.map(onlyRecord);
    assert.deepEqual(
      records.map((r) => r.body.stringValue),
      ["claude_code.session_start", "claude_code.instructions_loaded"],
    );
    const ids = records.map((r) => attributes(r)["session.id"]);
    assert.deepEqual(ids, [SESSION.session_id, SESSION.session_id]);
  } finally {
    await store.close();
  }
});

const PARENT_KEY = "skillworks.parent.session.id";

const PARENT = "7c4e2b9a-1d3f-4a6e-9b8c-5e0f2a7d1c93";

const PARENT_LISTS = [
  ["alone", `${PARENT_KEY}=${PARENT}`],
  ["first", `${PARENT_KEY}=${PARENT},team=studio,deployment.environment=dev`],
  ["in the middle", `team=studio,${PARENT_KEY}=${PARENT},deployment.environment=dev`],
  ["last", `team=studio,deployment.environment=dev,${PARENT_KEY}=${PARENT}`],
  ["among spaces", `team=studio , ${PARENT_KEY} = ${PARENT} , deployment.environment=dev`],
];

const NO_PARENT_LISTS = [
  ["no OTEL_RESOURCE_ATTRIBUTES", {}],
  ["an empty OTEL_RESOURCE_ATTRIBUTES", { OTEL_RESOURCE_ATTRIBUTES: "" }],
  ["other keys only", { OTEL_RESOURCE_ATTRIBUTES: "team=studio,deployment.environment=dev" }],
  ["a key that only ends with the Parent key", { OTEL_RESOURCE_ATTRIBUTES: `my.${PARENT_KEY}=${PARENT}` }],
];

for (const [name, payload] of EVENTS) {
  for (const [where, list] of PARENT_LISTS) {
    test(`${name} carries the Parent beside session.id when the Parent key sits ${where} in the list`, async () => {
      // Act
      const record = onlyRecord(await recordFor(payload, { OTEL_RESOURCE_ATTRIBUTES: list }));

      // Assert
      const got = attributes(record);
      assert.equal(got[PARENT_KEY], PARENT);
      assert.equal(got["session.id"], payload.session_id);
    });
  }

  for (const [state, extra] of NO_PARENT_LISTS) {
    test(`${name} with ${state} carries no Parent`, async () => {
      // Act
      const record = onlyRecord(await recordFor(payload, extra));

      // Assert
      const keys = record.attributes.map((a) => a.key);
      assert.ok(!keys.includes(PARENT_KEY), `${PARENT_KEY} is absent`);
      assert.equal(attributes(record)["session.id"], payload.session_id);
    });
  }
}

const REPOSITORY_ON = { OTEL_METRICS_INCLUDE_REPOSITORY: "true" };

function assertNoRepository(record) {
  const keys = record.attributes.map((a) => a.key);
  assert.ok(!keys.includes("vcs.owner.name"), "vcs.owner.name is absent");
  assert.ok(!keys.includes("vcs.repository.name"), "vcs.repository.name is absent");
}

const ORIGINS = [
  "https://github.com/octo-org/widgets.git",
  "https://github.com/octo-org/widgets",
  "git@github.com:octo-org/widgets.git",
  "ssh://git@github.com/octo-org/widgets.git",
];

for (const [name, payload] of [["a Load", REQUIRED], ["a Session", SESSION]]) {
  for (const origin of ORIGINS) {
    test(`${name} from a repository at ${origin} carries its owner and name with the switch on`, async () => {
      // Arrange
      const cwd = await repository(origin);

      // Act
      const record = onlyRecord(await recordFor({ ...payload, cwd }, REPOSITORY_ON));

      // Assert
      const got = attributes(record);
      assert.equal(got["vcs.owner.name"], "octo-org");
      assert.equal(got["vcs.repository.name"], "widgets");
    });
  }

  for (const [state, extra] of [["off", { OTEL_METRICS_INCLUDE_REPOSITORY: "false" }], ["unset", {}]]) {
    test(`${name} from a repository carries no Repository with the switch ${state}`, async () => {
      // Arrange
      const cwd = await repository(ORIGINS[0]);

      // Act
      const record = onlyRecord(await recordFor({ ...payload, cwd }, extra));

      // Assert
      assertNoRepository(record);
    });
  }

  for (const [where, cwdOf] of [
    ["a repository with no origin", () => repository(undefined)],
    ["a folder that is no repository", () => mkdtemp(join(temp, "plain-"))],
    ["a folder that does not exist", async () => join(temp, "gone")],
  ]) {
    test(`${name} from ${where} is still sent, without a Repository, and exits zero`, async () => {
      // Arrange
      const cwd = await cwdOf();

      // Act
      const record = onlyRecord(await recordFor({ ...payload, cwd }, REPOSITORY_ON));

      // Assert
      assertNoRepository(record);
      assert.equal(attributes(record).session_id, payload.session_id);
    });
  }
}
