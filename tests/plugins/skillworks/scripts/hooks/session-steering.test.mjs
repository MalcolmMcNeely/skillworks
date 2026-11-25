import { execFileSync, spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

const PLUGIN = join(import.meta.dirname, "..", "..", "..", "..", "..", "plugins", "skillworks");

const SCRIPT = join(PLUGIN, "scripts", "hooks", "session-steering.mjs");

let temp;
let work;
let nested;
let sidecar;

function git(where, ...args) {
  return execFileSync("git", ["-C", where, ...args], { encoding: "utf8" });
}

beforeEach(async () => {
  // The temporary folder can sit behind a link, and git names the folder it resolves to.
  temp = await realpath(await mkdtemp(join(tmpdir(), "session-steering-")));
  work = join(temp, "work");
  sidecar = join(temp, "work-skillworks");
  execFileSync("git", ["init", "--quiet", work]);
  git(work, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
    "commit", "--quiet", "--allow-empty", "-m", "Base");
  nested = join(work, ".spec-loop", "nested", "job");
  git(work, "worktree", "add", "--quiet", "-b", "job", nested);
});

afterEach(async () => {
  await rm(temp, { recursive: true, force: true });
});

async function inSidecar(name, text) {
  await mkdir(dirname(join(sidecar, name)), { recursive: true });
  await writeFile(join(sidecar, name), text);
}

async function sidecarSteering() {
  await inSidecar("docs/skillworks/loop.json", JSON.stringify({ tracker: "files", "target-branch": "pr" }));
  await inSidecar("CLAUDE.md", "# The team's rules\n\n@docs/skillworks/rules/words.md\n");
  await inSidecar("docs/skillworks/rules/words.md", "# Words\n\nNo source file uses a word that lost.\n");
}

// The developer's own Session may carry the driver's mark, and the hook would then never pull.
function start(cwd, marks = {}) {
  const payload = {
    session_id: "3f2a9c1e-5b7d-4e8f-a1c2-9d0e6b4f7a31",
    transcript_path: "/home/dev/.claude/projects/work/3f2a9c1e.jsonl",
    cwd,
    hook_event_name: "SessionStart",
    source: "startup",
  };
  return new Promise((done, fail) => {
    const env = { ...process.env, SKILLWORKS_LOOP_SESSION: "", ...marks };
    const child = spawn(process.execPath, [SCRIPT], { cwd: temp, env });
    let out = "";
    let err = "";
    child.stdout.on("data", (chunk) => (out += chunk));
    child.stderr.on("data", (chunk) => (err += chunk));
    child.on("error", fail);
    child.on("close", (status) => done({ status, out, err }));
    child.stdin.end(JSON.stringify(payload));
  });
}

async function contextFor(cwd, marks) {
  const ran = await start(cwd, marks);
  assert.equal(ran.status, 0, ran.err);
  assert.equal(ran.err, "");
  if (ran.out === "") return undefined;
  const answer = JSON.parse(ran.out).hookSpecificOutput;
  assert.equal(answer.hookEventName, "SessionStart");
  return answer.additionalContext;
}

test("the Plugin runs this script when a Session starts, from the Plugin root", async () => {
  // Act
  const hooks = JSON.parse(await readFile(join(PLUGIN, "hooks", "hooks.json"), "utf8")).hooks;

  // Assert
  const entries = hooks.SessionStart.flatMap((group) => group.hooks);
  assert.ok(entries.some((entry) => entry.command === "node" &&
    entry.args.join(" ") === "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/session-steering.mjs"));
});

test("the Plugin gives this script 300 seconds, so a pull held to 240 always stops first", async () => {
  // Act
  const hooks = JSON.parse(await readFile(join(PLUGIN, "hooks", "hooks.json"), "utf8")).hooks;

  // Assert
  const entry = hooks.SessionStart.flatMap((group) => group.hooks)
    .find((held) => held.args.join(" ").endsWith("/scripts/hooks/session-steering.mjs"));
  assert.equal(entry.timeout, 300);
});

test("a Session started under Sidecar Steering gets the Sidecar's CLAUDE.md", async () => {
  // Arrange
  await sidecarSteering();

  // Act
  const context = await contextFor(work);

  // Assert
  assert.match(context, /# The team's rules/);
});

test("a Session started in a worktree under Sidecar Steering gets each rule the Sidecar's CLAUDE.md imports", async () => {
  // Arrange
  await sidecarSteering();

  // Act
  const context = await contextFor(nested);

  // Assert
  assert.match(context, /No source file uses a word that lost\./);
});

function chainOf(length) {
  const files = { "CLAUDE.md": "# The team's rules\n\n@l1.md\n" };
  for (let link = 1; link <= length; link++) {
    const next = link < length ? `\n@l${link + 1}.md\n` : "";
    files[`l${link}.md`] = `# Link ${link}\n\nLink ${link} of the chain.\n${next}`;
  }
  return files;
}

test("a Session started under Sidecar Steering gets the Sidecar's imports five hops deep and none past them", async () => {
  // Arrange
  await sidecarSteering();
  for (const [name, text] of Object.entries(chainOf(6))) await inSidecar(name, text);

  // Act
  const context = await contextFor(work);

  // Assert
  assert.deepEqual([context.includes("Link 5 of the chain."), context.includes("Link 6 of the chain.")], [true, false], context);
});

test("a Session started with no loop.json in the Sidecar gets nothing from the hook", async () => {
  // Arrange
  await inSidecar("CLAUDE.md", "# The team's rules\n");

  // Act
  const context = await contextFor(work);

  // Assert
  assert.equal(context, undefined);
});

const IN_BOTH = "both the repo and the Sidecar hold docs/skillworks/loop.json";

async function inRepo(name, text) {
  await mkdir(dirname(join(work, name)), { recursive: true });
  await writeFile(join(work, name), text);
}

test("a Session started with a loop.json in both the repo and the Sidecar is warned, naming both", async () => {
  // Arrange
  await sidecarSteering();
  await inRepo("docs/skillworks/loop.json", JSON.stringify({ tracker: "files", "target-branch": "pr" }));

  // Act
  const context = await contextFor(work);

  // Assert
  const repoCopy = join(work, "docs/skillworks/loop.json").replaceAll("\\", "/");
  const sidecarCopy = join(sidecar, "docs/skillworks/loop.json").replaceAll("\\", "/");
  assert.ok(context.includes(`${IN_BOTH}, so neither may win: ${repoCopy} and ${sidecarCopy}. Remove one of the two.`),
    context);
});

test("a Session started with a loop.json in the repo alone gets nothing from the hook", async () => {
  // Arrange
  await inRepo("docs/skillworks/loop.json", JSON.stringify({ tracker: "github", "target-branch": "main" }));

  // Act
  const context = await contextFor(work);

  // Assert
  assert.equal(context, undefined);
});

test("a Session started under Sidecar Steering alone is not warned of a loop.json in both", async () => {
  // Arrange
  await sidecarSteering();

  // Act
  const context = await contextFor(work);

  // Assert
  assert.ok(!context.includes(IN_BOTH), context);
});

test("a Session started outside any repo gets nothing from the hook", async () => {
  // Act
  const context = await contextFor(temp);

  // Assert
  assert.equal(context, undefined);
});

const IDENTITY = ["-c", "user.name=Test", "-c", "user.email=test@example.invalid"];

const STEERING_REPO = () => join(temp, "steering.git");

const TEAMMATE = () => join(temp, "teammate");

async function commitAll(where, files) {
  for (const [name, text] of Object.entries(files)) {
    await mkdir(dirname(join(where, name)), { recursive: true });
    await writeFile(join(where, name), text);
  }
  git(where, "add", "-A");
  git(where, ...IDENTITY, "commit", "--quiet", "-m", "Steering");
}

const TEAM_STEERING = {
  "docs/skillworks/loop.json": JSON.stringify({ tracker: "files", "target-branch": "pr" }),
  "CLAUDE.md": "# The team's rules\n\n@docs/skillworks/rules/words.md\n",
  "docs/skillworks/rules/words.md": "# Words\n\nThe first version of the words.\n",
};

async function steeringRepo(files = TEAM_STEERING) {
  execFileSync("git", ["init", "--quiet", "--bare", "--initial-branch=main", STEERING_REPO()]);
  clone(STEERING_REPO(), TEAMMATE());
  await commitAll(TEAMMATE(), files);
  git(TEAMMATE(), "push", "--quiet", "-u", "origin", "main");
  clone(STEERING_REPO(), sidecar);
}

// The machine's own autocrlf would turn the rules' line ends, and the context shows them as they sit.
function clone(from, to) {
  execFileSync("git", ["clone", "--quiet", "-c", "core.autocrlf=false", from, to], { stdio: "ignore" });
}

async function teammatePushes(files) {
  await commitAll(TEAMMATE(), files);
  git(TEAMMATE(), "push", "--quiet", "origin", "main");
}

const NEWER_WORDS = { "docs/skillworks/rules/words.md": "# Words\n\nThe second version of the words.\n" };

test("a Session started under Sidecar Steering with a Steering repo loads the rules a teammate pushed", async () => {
  // Arrange
  await steeringRepo();
  await teammatePushes(NEWER_WORDS);

  // Act
  const context = await contextFor(work);

  // Assert
  assert.match(context, /The second version of the words\./);
});

const PULL_WARNING = /WARNING: the pull of the Steering repo into the Sidecar [^\n]+\. The Steering files on disk are read\./g;

function warningsIn(context) {
  return context.match(PULL_WARNING) ?? [];
}

test("a Session whose Steering repo is gone is warned once and loads the rules on disk", async () => {
  // Arrange
  await steeringRepo();
  await rm(STEERING_REPO(), { recursive: true, force: true });

  // Act
  const context = await contextFor(work);

  // Assert
  assert.deepEqual([warningsIn(context).length, /The first version of the words\./.test(context)], [1, true], context);
});

test("a Session whose uncommitted edit the pull would overwrite is warned and loads the edit", async () => {
  // Arrange
  await steeringRepo();
  await teammatePushes(NEWER_WORDS);
  await inSidecar("docs/skillworks/rules/words.md", "# Words\n\nMy own edit of the words.\n");

  // Act
  const context = await contextFor(work);

  // Assert
  assert.deepEqual([warningsIn(context).length, /My own edit of the words\./.test(context)], [1, true], context);
});

test("a Session whose Sidecar has no remote loads its rules and says nothing of a pull", async () => {
  // Arrange
  await sidecarSteering();
  execFileSync("git", ["init", "--quiet", sidecar]);

  // Act
  const context = await contextFor(work);

  // Assert
  assert.deepEqual([/pull/i.test(context), /No source file uses a word that lost\./.test(context)], [false, true], context);
});

// It takes git's connection and never answers it, so only the pull's limit can end the pull.
async function silentRemote() {
  const held = [];
  const server = createServer((socket) => {
    // The hook stops git mid-connection, and the reset it causes is what the stand-in expects.
    socket.on("error", () => {});
    held.push(socket);
  });
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  return {
    url: `git://127.0.0.1:${server.address().port}/steering.git`,
    close: () => {
      held.forEach((socket) => socket.destroy());
      server.close();
    },
  };
}

test("a Session whose Steering repo never answers is warned once the pull runs past its limit", async (t) => {
  // Arrange
  const loop = { tracker: "files", "target-branch": "pr", "steering-pull-seconds": 1 };
  await steeringRepo({ ...TEAM_STEERING, "docs/skillworks/loop.json": JSON.stringify(loop) });
  const remote = await silentRemote();
  t.after(remote.close);
  git(sidecar, "remote", "set-url", "origin", remote.url);

  // Act
  const context = await contextFor(work);

  // Assert
  assert.deepEqual(warningsIn(context), [
    "WARNING: the pull of the Steering repo into the Sidecar ran past its limit of 1 second. " +
    "The Steering files on disk are read.",
  ]);
});

const SHARED_SETTINGS = ".claude/settings.json";

const LOCAL_SETTINGS = () => join(work, ".claude", "settings.local.json");

const TEAM_SETTINGS = {
  permissions: { allow: ["Bash(git push)"], deny: ["WebSearch"] },
  autoMemoryEnabled: false,
};

const NEWER_SETTINGS = {
  permissions: { allow: ["Bash(git push)", "Bash(gh issue close:*)"], deny: ["WebSearch", "WebFetch"] },
  autoMemoryEnabled: false,
  promptCacheTtl: "1h",
  enabledPlugins: { "skillworks@skillworks": true },
};

const MY_SETTINGS = {
  permissions: { allow: ["Bash(git push)", "Bash(npm test)"], deny: ["Read(./.env)"], ask: ["Bash(rm:*)"] },
  autoMemoryEnabled: true,
  outputStyle: "Explanatory",
  enabledPlugins: { "mine@mine": true },
};

async function settingsRepo() {
  await steeringRepo({ ...TEAM_STEERING, [SHARED_SETTINGS]: JSON.stringify(TEAM_SETTINGS) });
  await mkdir(dirname(LOCAL_SETTINGS()), { recursive: true });
  await writeFile(LOCAL_SETTINGS(), JSON.stringify(MY_SETTINGS, null, 2));
}

async function localSettings() {
  return JSON.parse(await readFile(LOCAL_SETTINGS(), "utf8"));
}

test("a pull that changes the team's shared settings merges them into the main checkout's local settings", async () => {
  // Arrange
  await settingsRepo();
  await teammatePushes({ [SHARED_SETTINGS]: JSON.stringify(NEWER_SETTINGS) });

  // Act
  await contextFor(nested);

  // Assert
  const merged = await localSettings();
  assert.deepEqual(
    [merged.permissions.allow.includes("Bash(gh issue close:*)"), merged.permissions.deny.includes("WebFetch"),
      merged.promptCacheTtl, merged.autoMemoryEnabled],
    [true, true, "1h", false],
    JSON.stringify(merged));
});

test("a merge of the team's shared settings keeps every entry and key only the local settings held", async () => {
  // Arrange
  await settingsRepo();
  await teammatePushes({ [SHARED_SETTINGS]: JSON.stringify(NEWER_SETTINGS) });

  // Act
  await contextFor(work);

  // Assert
  const merged = await localSettings();
  assert.deepEqual(
    [merged.permissions.allow.includes("Bash(npm test)"), merged.permissions.deny.includes("Read(./.env)"),
      merged.permissions.ask, merged.outputStyle, merged.enabledPlugins["mine@mine"]],
    [true, true, ["Bash(rm:*)"], "Explanatory", true],
    JSON.stringify(merged));
});

test("a Session whose pull changed the team's shared settings is told the change applies from the next Session", async () => {
  // Arrange
  await settingsRepo();
  await teammatePushes({ [SHARED_SETTINGS]: JSON.stringify(NEWER_SETTINGS) });

  // Act
  const ran = await start(work);

  // Assert
  const answer = JSON.parse(ran.out);
  const told = /The change applies from the next Session\./;
  assert.deepEqual([told.test(answer.systemMessage), told.test(answer.hookSpecificOutput.additionalContext)],
    [true, true], ran.out);
});

test("a pull that leaves the team's shared settings as they were leaves the local settings untouched", async () => {
  // Arrange
  await settingsRepo();
  await teammatePushes(NEWER_WORDS);
  const before = await readFile(LOCAL_SETTINGS(), "utf8");

  // Act
  const context = await contextFor(work);

  // Assert
  assert.deepEqual([await readFile(LOCAL_SETTINGS(), "utf8"), /settings/i.test(context)], [before, false], context);
});

test("a loop Session, given the driver's mark, loads the rules on disk and does not pull", async () => {
  // Arrange
  await steeringRepo();
  await teammatePushes(NEWER_WORDS);

  // Act
  const context = await contextFor(work, { SKILLWORKS_LOOP_SESSION: "1" });

  // Assert
  assert.match(context, /The first version of the words\./);
});
