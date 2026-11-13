import { execFileSync, spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

const PLUGIN = join(import.meta.dirname, "..", "..", "..", "..", "..", "plugins", "skillworks");

const SCRIPT = join(PLUGIN, "scripts", "hooks", "sidecar-steering.mjs");

let temp;
let work;
let nested;
let sidecar;

function git(where, ...args) {
  return execFileSync("git", ["-C", where, ...args], { encoding: "utf8" });
}

beforeEach(async () => {
  // The temporary folder can sit behind a link, and git names the folder it resolves to.
  temp = await realpath(await mkdtemp(join(tmpdir(), "sidecar-steering-")));
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

function start(cwd) {
  const payload = {
    session_id: "3f2a9c1e-5b7d-4e8f-a1c2-9d0e6b4f7a31",
    transcript_path: "/home/dev/.claude/projects/work/3f2a9c1e.jsonl",
    cwd,
    hook_event_name: "SessionStart",
    source: "startup",
  };
  return new Promise((done, fail) => {
    const child = spawn(process.execPath, [SCRIPT], { cwd: temp });
    let out = "";
    let err = "";
    child.stdout.on("data", (chunk) => (out += chunk));
    child.stderr.on("data", (chunk) => (err += chunk));
    child.on("error", fail);
    child.on("close", (status) => done({ status, out, err }));
    child.stdin.end(JSON.stringify(payload));
  });
}

async function contextFor(cwd) {
  const ran = await start(cwd);
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
    entry.args.join(" ") === "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/sidecar-steering.mjs"));
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

test("a Session started with no loop.json in the Sidecar gets nothing from the hook", async () => {
  // Arrange
  await inSidecar("CLAUDE.md", "# The team's rules\n");

  // Act
  const context = await contextFor(work);

  // Assert
  assert.equal(context, undefined);
});

test("a Session started outside any repo gets nothing from the hook", async () => {
  // Act
  const context = await contextFor(temp);

  // Assert
  assert.equal(context, undefined);
});
