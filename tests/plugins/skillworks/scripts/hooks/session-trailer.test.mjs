import { execFileSync, spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { platform, tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

const ROOT = join(import.meta.dirname, "..", "..", "..", "..", "..");

const PLUGIN = join(ROOT, "plugins", "skillworks");

const SCRIPT = join(PLUGIN, "scripts", "hooks", "session-trailer.mjs");

const SESSION = "3f2a9c1e-5b7d-4e8f-a1c2-9d0e6b4f7a31";

const SECOND_SESSION = "7c4e2b9a-1d3f-4a6e-9b8c-5e0f2a7d1c93";

const TRAILER = `--trailer "Skillworks-Session: ${SESSION}"`;

const READ_BACK = "--format=%(trailers:key=Skillworks-Session,valueonly)";

let temp;

beforeEach(async () => {
  temp = await mkdtemp(join(tmpdir(), "session-trailer-"));
});

afterEach(async () => {
  await rm(temp, { recursive: true, force: true });
});

function input(command, session = SESSION) {
  return {
    session_id: session,
    transcript_path: "/home/dev/.claude/projects/work/3f2a9c1e.jsonl",
    cwd: "/home/dev/work",
    permission_mode: "default",
    hook_event_name: "PreToolUse",
    tool_name: "Bash",
    tool_input: { command, description: "Commit the work", timeout: 120000 },
    tool_use_id: "toolu_01ABC123",
  };
}

function hook(payload, extra = {}) {
  const env = { ...process.env, ...extra };
  return new Promise((done, fail) => {
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

async function answerTo(command, session) {
  const ran = await hook(input(command, session));
  assert.equal(ran.status, 0, ran.err);
  assert.equal(ran.err, "");
  return ran.out === "" ? undefined : JSON.parse(ran.out).hookSpecificOutput;
}

async function rewritten(command, session) {
  const answer = await answerTo(command, session);
  assert.ok(answer?.updatedInput, `the hook handed back no command for: ${command}`);
  assert.equal(answer.hookEventName, "PreToolUse");
  assert.equal(answer.permissionDecision, undefined, "a rewrite leaves the decision to the user's permissions");
  return answer.updatedInput.command;
}

// Git for Windows ships its own bash, and the bash first on PATH there may be another system's.
function bash() {
  if (platform() !== "win32") return "bash";
  const core = execFileSync("git", ["--exec-path"], { encoding: "utf8" }).trim();
  return resolve(core, "..", "..", "..", "bin", "bash.exe");
}

const BASH = bash();

async function repository() {
  const dir = await mkdtemp(join(temp, "repository-"));
  const config = join(temp, "gitconfig");
  await writeFile(
    config,
    "[user]\n\tname = Test\n\temail = test@example.invalid\n[commit]\n\tgpgsign = false\n[core]\n\tautocrlf = false\n",
  );
  const env = { ...process.env, GIT_CONFIG_GLOBAL: config, GIT_CONFIG_NOSYSTEM: "1" };
  execFileSync("git", ["init", "--quiet", "--initial-branch=main", dir], { env });
  await writeFile(join(dir, "work.txt"), "work\n");
  const run = (command) => execFileSync(BASH, ["-c", command], { cwd: dir, env, encoding: "utf8" });
  const git = (...args) => execFileSync("git", ["-C", dir, ...args], { env, encoding: "utf8" });
  return { dir: dir.replaceAll("\\", "/"), run, git };
}

function sessions(repo) {
  return repo.git("log", "-1", READ_BACK).trim().split("\n").filter(Boolean);
}

test("the Plugin runs this script before the Bash tool, from the Plugin root", async () => {
  // Act
  const hooks = JSON.parse(await readFile(join(PLUGIN, "hooks", "hooks.json"), "utf8")).hooks;

  // Assert
  assert.equal(hooks.PreToolUse.length, 1);
  const [group] = hooks.PreToolUse;
  assert.equal(group.matcher, "Bash");
  const [entry] = group.hooks;
  assert.equal(entry.type, "command");
  assert.equal(entry.command, "node");
  assert.deepEqual(entry.args, ["${CLAUDE_PLUGIN_ROOT}/scripts/hooks/session-trailer.mjs"]);
});

for (const command of [
  "ls -la",
  "git status",
  "git log --grep commit",
  'echo "commit"',
  "git log --oneline | grep commit",
  'echo "git commit"',
  "git commit-tree HEAD^{tree} -m x",
  "cat <<'EOF'\ngit commit -m x\nEOF",
  "gh issue comment 254 --body 'run git commit'",
  "npm test # then git commit",
]) {
  test(`a command with no git commit passes unchanged: ${command}`, async () => {
    // Act
    const answer = await answerTo(command);

    // Assert
    assert.equal(answer, undefined);
  });
}

for (const [form, command, expected] of [
  ["-m", 'git commit -m "Fix the thing"', `git commit ${TRAILER} -m "Fix the thing"`],
  ["-F", "git commit -F message.txt", `git commit ${TRAILER} -F message.txt`],
  [
    "a heredoc message",
    "git commit -F - <<'EOF'\nFix (the) thing\n\nTicket: #254\nEOF",
    `git commit ${TRAILER} -F - <<'EOF'\nFix (the) thing\n\nTicket: #254\nEOF`,
  ],
  [
    "a heredoc in a substitution",
    "git commit -m \"$(cat <<'EOF'\nFix it) and git commit again\nEOF\n)\"",
    `git commit ${TRAILER} -m "$(cat <<'EOF'\nFix it) and git commit again\nEOF\n)"`,
  ],
  ["an && chain", 'git add -A && git commit -m "x"', `git add -A && git commit ${TRAILER} -m "x"`],
  ["an || chain", 'git diff --quiet || git commit -am "x"', `git diff --quiet || git commit ${TRAILER} -am "x"`],
  ["a ; chain", 'git add -A; git commit -m "x"; git log -1', `git add -A; git commit ${TRAILER} -m "x"; git log -1`],
  ["-C", 'git -C "C:/work tree" commit -m x', `git -C "C:/work tree" commit ${TRAILER} -m x`],
  ["-c", "git -c user.name=Bot commit -m x", `git -c user.name=Bot commit ${TRAILER} -m x`],
  ["--amend", "git commit --amend --no-edit", `git commit ${TRAILER} --amend --no-edit`],
  ["an environment before git", "GIT_AUTHOR_NAME=Bot git commit -m x", `GIT_AUTHOR_NAME=Bot git commit ${TRAILER} -m x`],
  ["a subshell", '(cd sub && git commit -m "x")', `(cd sub && git commit ${TRAILER} -m "x")`],
  [
    "two commits",
    "git commit -m a && git commit --allow-empty -m b",
    `git commit ${TRAILER} -m a && git commit ${TRAILER} --allow-empty -m b`,
  ],
]) {
  test(`a commit given ${form} gets the trailer right after commit`, async () => {
    // Act
    const got = await rewritten(command);

    // Assert
    assert.equal(got, expected);
  });
}

test("a rewrite keeps every other field of the tool input", async () => {
  // Act
  const answer = await answerTo("git commit -m x");

  // Assert
  assert.deepEqual(answer.updatedInput, { ...input("").tool_input, command: `git commit ${TRAILER} -m x` });
});

for (const [state, extra] of [
  ["on", { OTEL_EXPORTER_OTLP_ENDPOINT: "http://127.0.0.1:1" }],
  ["off", { OTEL_EXPORTER_OTLP_ENDPOINT: "" }],
]) {
  test(`a commit gets the trailer with telemetry ${state}`, async () => {
    // Act
    const ran = await hook(input("git commit -m x"), extra);

    // Assert
    assert.equal(ran.status, 0, ran.err);
    assert.equal(JSON.parse(ran.out).hookSpecificOutput.updatedInput.command, `git commit ${TRAILER} -m x`);
  });
}

for (const [form, command] of [
  ["bash -c", "bash -c 'git add -A && git commit -m x'"],
  ["sh -c", 'sh -c "git commit -m x"'],
  ["eval", 'eval "git commit -m x"'],
  ["backticks", "echo `git commit -m x`"],
  ["xargs", "echo x | xargs git commit -m"],
  ["a chain beside a plain commit", "git commit -m a && bash -c 'git commit -m b'"],
]) {
  test(`a commit inside ${form} is denied with the plain-command reason`, async () => {
    // Act
    const answer = await answerTo(command);

    // Assert
    assert.equal(answer.permissionDecision, "deny");
    assert.match(answer.permissionDecisionReason, /Run `git commit` as a plain command of its own/);
    assert.equal(answer.updatedInput, undefined);
  });
}

test("bash -c holding no commit passes unchanged", async () => {
  // Act
  const answer = await answerTo("bash -c 'git log --grep commit'");

  // Assert
  assert.equal(answer, undefined);
});

test("a commit with no Session id to write is denied", async () => {
  // Act
  const answer = await answerTo("git commit -m x", null);

  // Assert
  assert.equal(answer.permissionDecision, "deny");
});

for (const [form, commandIn] of [
  ["-m", () => 'git add -A && git commit -m "Fix the thing"'],
  ["a heredoc in a substitution", () => "git add -A && git commit -m \"$(cat <<'EOF'\nFix (the) thing\n\nMore.\nEOF\n)\""],
  ["-C", (repo) => `git add -A && git -C "${repo.dir}" commit -m "Fix the thing"`],
]) {
  test(`git reads the Session back from a commit made by the rewritten command, given ${form}`, async () => {
    // Arrange
    const repo = await repository();
    const command = await rewritten(commandIn(repo));

    // Act
    repo.run(command);

    // Assert
    assert.deepEqual(sessions(repo), [SESSION]);
  });
}

test("the trailer joins the block that holds Ticket and Co-Authored-By", async () => {
  // Arrange
  const repo = await repository();
  const message = "Fix the thing\n\nThe body.\n\nTicket: #254\nCo-Authored-By: Claude <noreply@anthropic.com>\n";
  await writeFile(join(repo.dir, "message.txt"), message);
  const command = await rewritten("git add work.txt && git commit -F message.txt");

  // Act
  repo.run(command);

  // Assert
  const block = repo.git("log", "-1", "--format=%(trailers:only,unfold)").trim();
  assert.deepEqual(block.split("\n"), [
    "Ticket: #254",
    "Co-Authored-By: Claude <noreply@anthropic.com>",
    `Skillworks-Session: ${SESSION}`,
  ]);
});

test("an amend by the same Session adds no second line, and one by a second Session adds one", async () => {
  // Arrange
  const repo = await repository();
  repo.run(await rewritten('git add -A && git commit -m "Fix the thing"'));
  const amend = "git commit --amend --no-edit";

  // Act
  repo.run(await rewritten(amend));
  const afterSame = sessions(repo);
  repo.run(await rewritten(amend, SECOND_SESSION));
  const afterSecond = sessions(repo);

  // Assert
  assert.deepEqual(afterSame, [SESSION]);
  assert.deepEqual(afterSecond, [SESSION, SECOND_SESSION]);
});
