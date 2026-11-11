import { execFileSync, spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

const ROOT = join(import.meta.dirname, "..", "..", "..", "..", "..");

const PLUGIN = join(ROOT, "plugins", "skillworks");

const SCRIPT = join(PLUGIN, "scripts", "hooks", "export-steering.mjs");

// The hook is Node and cannot import the name, so a rename there turns these tests red until the hook follows it.
const STEERING_BRANCH = (await readFile(join(PLUGIN, "scripts", "export", "export_branch.py"), "utf8")).match(
  /^STEERING = "([^"]+)"$/m,
)[1];

const LINE = "This branch holds no Steering. Read each path under `docs/skillworks/` with `steering-file <path>`.";

const STEERING_CLAUDE = [
  "# The team's project",
  "",
  "## Agent skills",
  "",
  "See `docs/skillworks/issue-tracker.md` for the Tracker.",
  "",
  "@docs/skillworks/rules/comments.md",
  "@docs/skillworks/rules/testing.md",
  "",
  "An address such as `see @docs/skillworks/rules/in-a-span.md` in a code span is never loaded.",
  "",
  "```",
  "@docs/skillworks/rules/in-a-block.md",
  "```",
  "",
].join("\n");

const STEERING = {
  "CLAUDE.md": STEERING_CLAUDE,
  "docs/skillworks/loop.json": '{ "tracker": "github", "target-branch": "pr", "export": true }\n',
  "docs/skillworks/rules/comments.md": "# Comments\n\nA comment records why.\n\n@more/doc-comments.md\n",
  "docs/skillworks/rules/more/doc-comments.md": "# Doc comments\n\nNo file has doc comments.\n",
  "docs/skillworks/rules/testing.md": "# Testing\n\nTests are integration style.\n",
  "docs/skillworks/rules/in-a-span.md": "# In a span\n\nNamed only inside a code span.\n",
  "docs/skillworks/rules/in-a-block.md": "# In a block\n\nNamed only inside a code block.\n",
};

let temp;

beforeEach(async () => {
  temp = await mkdtemp(join(tmpdir(), "export-steering-"));
});

afterEach(async () => {
  await rm(temp, { recursive: true, force: true });
});

async function gitEnv() {
  const config = join(temp, "gitconfig");
  await writeFile(
    config,
    "[user]\n\tname = Test\n\temail = test@example.invalid\n[commit]\n\tgpgsign = false\n[core]\n\tautocrlf = false\n",
  );
  return { ...process.env, GIT_CONFIG_GLOBAL: config, GIT_CONFIG_NOSYSTEM: "1" };
}

async function writeAll(dir, files) {
  for (const [path, content] of Object.entries(files)) {
    await mkdir(dirname(join(dir, path)), { recursive: true });
    await writeFile(join(dir, path), content);
  }
}

async function exportCheckout({ steering = true } = {}) {
  const env = await gitEnv();
  const origin = join(temp, "origin.git");
  const dir = join(temp, "work");
  const git = (...args) => execFileSync("git", ["-C", dir, ...args], { env, encoding: "utf8" });
  execFileSync("git", ["init", "--quiet", "--bare", "--initial-branch=main", origin], { env });
  execFileSync("git", ["init", "--quiet", "--initial-branch=main", dir], { env });
  git("remote", "add", "origin", origin);
  await writeAll(dir, { "CLAUDE.md": "# The team's own notes\n", "work.txt": "work\n" });
  git("add", "-A");
  git("commit", "--quiet", "-m", "The team's work");
  git("push", "--quiet", "origin", "main");
  if (steering) {
    git("switch", "--quiet", "-c", STEERING_BRANCH);
    await writeAll(dir, STEERING);
    git("add", "-A");
    git("commit", "--quiet", "-m", "Steering");
    git("push", "--quiet", "origin", STEERING_BRANCH);
    git("switch", "--quiet", "main");
    git("branch", "--quiet", "-D", STEERING_BRANCH);
  }
  git("fetch", "--quiet", "origin");
  git("switch", "--quiet", "-c", "feature/PROJ-12/slug");
  return { dir, git, env, origin };
}

function payload(cwd) {
  return {
    session_id: "3f2a9c1e-5b7d-4e8f-a1c2-9d0e6b4f7a31",
    transcript_path: "/home/dev/.claude/projects/work/3f2a9c1e.jsonl",
    cwd,
    hook_event_name: "SessionStart",
    source: "startup",
    model: "claude-opus-5-5",
  };
}

function hook(cwd, env) {
  return new Promise((done, fail) => {
    const child = spawn(process.execPath, [SCRIPT], { cwd: temp, env });
    let out = "";
    let err = "";
    child.stdout.on("data", (chunk) => (out += chunk));
    child.stderr.on("data", (chunk) => (err += chunk));
    child.on("error", fail);
    child.on("close", (status) => done({ status, out, err }));
    child.stdin.end(JSON.stringify(payload(cwd)));
  });
}

async function contextFor(repo, cwd = repo.dir) {
  const ran = await hook(cwd, repo.env);
  assert.equal(ran.status, 0, ran.err);
  if (ran.out === "") return undefined;
  const answer = JSON.parse(ran.out).hookSpecificOutput;
  assert.equal(answer.hookEventName, "SessionStart");
  return answer.additionalContext;
}

test("the Plugin runs this script when a session starts, from the Plugin root", async () => {
  // Act
  const hooks = JSON.parse(await readFile(join(PLUGIN, "hooks", "hooks.json"), "utf8")).hooks;

  // Assert
  const entries = hooks.SessionStart.flatMap((group) => group.hooks);
  assert.ok(
    entries.some(
      (entry) =>
        entry.type === "command" &&
        entry.command === "node" &&
        entry.args?.[0] === "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/export-steering.mjs" &&
        entry.timeout <= 5,
    ),
  );
});

test("a session on an Export branch gets the Steering branch's CLAUDE.md", async () => {
  // Arrange
  const repo = await exportCheckout();

  // Act
  const context = await contextFor(repo);

  // Assert
  assert.ok(context?.includes(STEERING_CLAUDE), context);
});

test("a session on an Export branch gets each file the Steering CLAUDE.md imports, and the files those import", async () => {
  // Arrange
  const repo = await exportCheckout();

  // Act
  const context = await contextFor(repo);

  // Assert
  const imported = ["docs/skillworks/rules/comments.md", "docs/skillworks/rules/testing.md", "docs/skillworks/rules/more/doc-comments.md"];
  assert.deepEqual(
    imported.filter((path) => !context?.includes(STEERING[path])),
    [],
  );
});

test("a session on an Export branch is told to read each Steering path with steering-file", async () => {
  // Arrange
  const repo = await exportCheckout();

  // Act
  const context = await contextFor(repo);

  // Assert
  assert.ok(context?.includes(LINE), context);
});

test("a session started in a folder below the repo root on an Export branch still gets the Steering", async () => {
  // Arrange
  const repo = await exportCheckout();
  await mkdir(join(repo.dir, "src"), { recursive: true });

  // Act
  const context = await contextFor(repo, join(repo.dir, "src"));

  // Assert
  assert.ok(context?.includes(LINE), context);
});

test("an address in a code span or a code block is not loaded as an import", async () => {
  // Arrange
  const repo = await exportCheckout();

  // Act
  const context = await contextFor(repo);

  // Assert
  assert.ok(
    context?.includes(LINE) &&
      !context.includes(STEERING["docs/skillworks/rules/in-a-span.md"]) &&
      !context.includes(STEERING["docs/skillworks/rules/in-a-block.md"]),
    context,
  );
});

test("a session on a branch with loop.json on disk gets nothing new", async () => {
  // Arrange
  const repo = await exportCheckout();
  await writeAll(repo.dir, { "docs/skillworks/loop.json": STEERING["docs/skillworks/loop.json"] });

  // Act
  const context = await contextFor(repo);

  // Assert
  assert.equal(context, undefined);
});

test("a session on a branch that holds loop.json only at the old Steering path still gets the Steering", async () => {
  // Arrange
  const repo = await exportCheckout();
  await writeAll(repo.dir, { "docs/agents/loop.json": STEERING["docs/skillworks/loop.json"] });

  // Act
  const context = await contextFor(repo);

  // Assert
  assert.ok(context?.includes(LINE), context);
});

test("a session on an Export branch with no local origin/skillworks/steering gets nothing new", async () => {
  // Arrange
  const repo = await exportCheckout({ steering: false });

  // Act
  const context = await contextFor(repo);

  // Assert
  assert.equal(context, undefined);
});

test("a session outside any git repository gets nothing new", async () => {
  // Arrange
  const repo = { dir: join(temp, "plain"), env: await gitEnv() };
  await mkdir(repo.dir);

  // Act
  const context = await contextFor(repo);

  // Assert
  assert.equal(context, undefined);
});

test("the hook reads the local origin/skillworks/steering as the last fetch left it, and never fetches", async () => {
  // Arrange
  const repo = await exportCheckout();
  const other = join(temp, "other");
  execFileSync("git", ["clone", "--quiet", "--branch", STEERING_BRANCH, repo.origin, other], { env: repo.env });
  await writeFile(join(other, "docs", "skillworks", "rules", "testing.md"), "# Testing\n\nA rule changed on another machine.\n");
  execFileSync("git", ["-C", other, "commit", "--quiet", "-am", "Change the testing rule"], { env: repo.env });
  execFileSync("git", ["-C", other, "push", "--quiet", "origin", STEERING_BRANCH], { env: repo.env });

  // Act
  const context = await contextFor(repo);

  // Assert
  assert.ok(context?.includes(STEERING["docs/skillworks/rules/testing.md"]), context);
});

test("the hook writes nothing to the working tree", async () => {
  // Arrange
  const repo = await exportCheckout();

  // Act
  await contextFor(repo);

  // Assert
  assert.equal(repo.git("status", "--porcelain", "--untracked-files=all", "--ignored"), "");
});
