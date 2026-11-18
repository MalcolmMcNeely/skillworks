import { execFileSync, spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, realpath, rename, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

const PLUGIN = join(import.meta.dirname, "..", "..", "..", "..", "..", "plugins", "skillworks");

const SCRIPT = join(PLUGIN, "scripts", "hooks", "session-steering.mjs");

let temp;
let work;
let nested;
let sidecar;

function home() {
  return join(temp, "home");
}

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

const SESSION = "3f2a9c1e-5b7d-4e8f-a1c2-9d0e6b4f7a31";

function start(cwd, session) {
  const payload = {
    session_id: session,
    transcript_path: "/home/dev/.claude/projects/work/3f2a9c1e.jsonl",
    cwd,
    hook_event_name: "SessionStart",
    source: "startup",
  };
  return new Promise((done, fail) => {
    // The developer's own user files would otherwise name a remote this test never made.
    const env = { ...process.env, HOME: home(), USERPROFILE: home() };
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

async function contextFor(cwd, session = SESSION) {
  const ran = await start(cwd, session);
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

const CLIENT_ORIGIN = "https://example.invalid/client/shop.git";

const IDENTITY = ["-c", "user.name=Test", "-c", "user.email=test@example.invalid"];

function remoteUrl() {
  return pathToFileURL(join(temp, "remote.git")).href;
}

async function remoteSteering() {
  execFileSync("git", ["init", "--quiet", "--bare", "--initial-branch=main", join(temp, "remote.git")]);
  execFileSync("git", ["init", "--quiet", "--initial-branch=main", join(temp, "remote-work")]);
  git(join(temp, "remote-work"), "remote", "add", "origin", remoteUrl());
  git(join(temp, "remote-work"), "config", "core.autocrlf", "false");
}

async function pushToRemote(files) {
  const remoteWork = join(temp, "remote-work");
  for (const [name, text] of Object.entries(files)) {
    await mkdir(dirname(join(remoteWork, name)), { recursive: true });
    await writeFile(join(remoteWork, name), text);
  }
  git(remoteWork, "add", "-A");
  git(remoteWork, ...IDENTITY, "commit", "--quiet", "-m", "Method");
  git(remoteWork, "push", "--quiet", "origin", "main");
}

async function named() {
  git(work, "remote", "add", "origin", CLIENT_ORIGIN);
  await mkdir(join(home(), ".skillworks"), { recursive: true });
  await writeFile(join(home(), ".skillworks", "remote-steering.json"),
    JSON.stringify({ url: remoteUrl(), repos: [CLIENT_ORIGIN] }));
}

const METHOD = {
  "CLAUDE.md": "# My method\n\n@docs/skillworks/rules/method.md\n",
  "docs/skillworks/rules/method.md": "# Method\n\nEvery change starts from a failing test.\n",
};

test("a Session started in a named repo gets the remote's CLAUDE.md", async () => {
  // Arrange
  await remoteSteering();
  await pushToRemote(METHOD);
  await named();

  // Act
  const context = await contextFor(work);

  // Assert
  assert.match(context ?? "", /# My method/);
});

test("a Session started in a named repo gets each file the remote's CLAUDE.md imports", async () => {
  // Arrange
  await remoteSteering();
  await pushToRemote(METHOD);
  await named();

  // Act
  const context = await contextFor(work);

  // Assert
  assert.match(context ?? "", /Every change starts from a failing test\./);
});

function chainOf(length) {
  const files = { "CLAUDE.md": "# My method\n\n@l1.md\n" };
  for (let link = 1; link <= length; link++) {
    const next = link < length ? `\n@l${link + 1}.md\n` : "";
    files[`l${link}.md`] = `# Link ${link}\n\nLink ${link} of the chain.\n${next}`;
  }
  return files;
}

test("a Session started in a named repo gets the remote's imports five hops deep, as the Sidecar walk does", async () => {
  // Arrange
  await remoteSteering();
  await pushToRemote(chainOf(6));
  await named();

  // Act
  const context = await contextFor(work);

  // Assert
  assert.match(context ?? "", /Link 5 of the chain\./);
});

test("a Session started in a named repo gets no remote import past five hops", async () => {
  // Arrange
  await remoteSteering();
  await pushToRemote(chainOf(6));
  await named();

  // Act
  const context = await contextFor(work) ?? "";

  // Assert
  assert.deepEqual([context.includes("Link 5 of the chain."), context.includes("Link 6 of the chain.")], [true, false], context);
});

test("a Session gets the remote's text from the commit it holds, and not from a later push", async () => {
  // Arrange
  await remoteSteering();
  await pushToRemote({ "CLAUDE.md": "# My method\n\nThe first version.\n" });
  await named();
  await contextFor(work);
  await pushToRemote({ "CLAUDE.md": "# My method\n\nThe second version.\n" });

  // Act
  const context = await contextFor(work);

  // Assert
  assert.match(context ?? "", /The first version\./);
});

test("a Session started under Sidecar Steering in a named repo gets the Sidecar's CLAUDE.md and the remote's", async () => {
  // Arrange
  await sidecarSteering();
  await remoteSteering();
  await pushToRemote(METHOD);
  await named();

  // Act
  const context = await contextFor(work);

  // Assert
  assert.deepEqual([/# The team's rules/.test(context ?? ""), /# My method/.test(context ?? "")], [true, true], context);
});

test("a Session started under Sidecar Steering in a repo that is not named gets what it got before", async () => {
  // Arrange
  await sidecarSteering();
  const before = await contextFor(work);
  await remoteSteering();
  await pushToRemote(METHOD);
  await named();
  git(work, "remote", "set-url", "origin", "https://example.invalid/another.git");

  // Act
  const context = await contextFor(work);

  // Assert
  assert.equal(context, before);
});

test("a Session started in a repo that is not named gets nothing from the hook", async () => {
  // Arrange
  await remoteSteering();
  await pushToRemote(METHOD);
  await named();
  git(work, "remote", "set-url", "origin", "https://example.invalid/another.git");

  // Act
  const context = await contextFor(work);

  // Assert
  assert.equal(context, undefined);
});

test("a Session started in a named repo whose remote cannot be fetched is warned that the text may be old", async () => {
  // Arrange
  await remoteSteering();
  await pushToRemote(METHOD);
  await named();
  await contextFor(work);
  await rename(join(temp, "remote.git"), join(temp, "moved.git"));

  // Act
  const context = await contextFor(work, "a-later-session");

  // Assert
  assert.match(context ?? "", /^WARNING: remote Steering at \S+ could not be fetched.*may be old/s);
});
