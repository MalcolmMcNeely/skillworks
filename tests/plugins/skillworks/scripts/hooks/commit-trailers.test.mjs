import { execFileSync, spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { platform, tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

const ROOT = join(import.meta.dirname, "..", "..", "..", "..", "..");

const PLUGIN = join(ROOT, "plugins", "skillworks");

const SCRIPT = join(PLUGIN, "scripts", "hooks", "commit-trailers.mjs");

const SESSION = "3f2a9c1e-5b7d-4e8f-a1c2-9d0e6b4f7a31";

const SECOND_SESSION = "7c4e2b9a-1d3f-4a6e-9b8c-5e0f2a7d1c93";

const TRAILER = `--trailer "Skillworks-Session: ${SESSION}"`;

const PS_TRAILER = `--trailer 'Skillworks-Session: ${SESSION}'`;

const TICKET_VARIABLE = "SKILLWORKS_TICKET";

const CREDIT = "Claude <noreply@anthropic.com>";

let temp;

beforeEach(async () => {
  temp = await mkdtemp(join(tmpdir(), "commit-trailers-"));
});

afterEach(async () => {
  await rm(temp, { recursive: true, force: true });
});

function input(command, session = SESSION, tool = "Bash", cwd = "/home/dev/work") {
  return {
    session_id: session,
    transcript_path: "/home/dev/.claude/projects/work/3f2a9c1e.jsonl",
    cwd,
    permission_mode: "default",
    hook_event_name: "PreToolUse",
    tool_name: tool,
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

// The Session running these tests may have been handed a ticket, and a test sets its own or none.
async function answerTo(command, session, tool, ticket = "", cwd = undefined) {
  const ran = await hook(input(command, session, tool, cwd), { [TICKET_VARIABLE]: ticket });
  assert.equal(ran.status, 0, ran.err);
  assert.equal(ran.err, "");
  return ran.out === "" ? undefined : JSON.parse(ran.out).hookSpecificOutput;
}

async function rewritten(command, session, tool, ticket, cwd) {
  const answer = await answerTo(command, session, tool, ticket, cwd);
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

function powerShell() {
  try {
    execFileSync("pwsh", ["-NoProfile", "-NonInteractive", "-Command", "exit 0"]);
    return "pwsh";
  } catch {
    return undefined;
  }
}

const PWSH = powerShell();

const NO_PWSH = PWSH ? false : "pwsh is not installed, so no PowerShell can run the rewritten command";

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
  // The script sits outside the repository, so git add -A never takes it into the commit.
  const runPowerShell = async (command) => {
    const script = join(temp, "command.ps1");
    await writeFile(script, `$ErrorActionPreference = 'Stop'\n$PSNativeCommandUseErrorActionPreference = $true\n${command}\n`);
    return execFileSync(PWSH, ["-NoProfile", "-NonInteractive", "-File", script], { cwd: dir, env, encoding: "utf8" });
  };
  return { dir: dir.replaceAll("\\", "/"), run, runPowerShell, git };
}

async function creditRepository(answer) {
  const repo = await repository();
  await mkdir(join(repo.dir, "docs", "agents"), { recursive: true });
  const settings = { tracker: "github", "target-branch": "main" };
  if (answer) settings["co-authored-by"] = answer;
  await writeFile(join(repo.dir, "docs", "agents", "loop.json"), JSON.stringify(settings));
  return repo;
}

function credits(repo) {
  return trailerValues(repo, "Co-Authored-By");
}

function trailerValues(repo, key) {
  return repo.git("log", "-1", `--format=%(trailers:key=${key},valueonly)`).trim().split("\n").filter(Boolean);
}

function sessions(repo) {
  return trailerValues(repo, "Skillworks-Session");
}

function tickets(repo) {
  return trailerValues(repo, "Ticket");
}

test("the Plugin runs this script before the Bash and PowerShell tools, from the Plugin root", async () => {
  // Act
  const hooks = JSON.parse(await readFile(join(PLUGIN, "hooks", "hooks.json"), "utf8")).hooks;

  // Assert
  assert.equal(hooks.PreToolUse.length, 1);
  const [group] = hooks.PreToolUse;
  assert.equal(group.matcher, "Bash|PowerShell");
  const [entry] = group.hooks;
  assert.equal(entry.type, "command");
  assert.equal(entry.command, "node");
  assert.deepEqual(entry.args, ["${CLAUDE_PLUGIN_ROOT}/scripts/hooks/commit-trailers.mjs"]);
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
  ["-m", 'git commit -m "Fix the thing"', `git commit -m "Fix the thing" ${TRAILER}`],
  ["-F", "git commit -F message.txt", `git commit -F message.txt ${TRAILER}`],
  [
    "a heredoc message",
    "git commit -F - <<'EOF'\nFix (the) thing\n\nTicket: #254\nEOF",
    `git commit -F - <<'EOF' ${TRAILER}\nFix (the) thing\n\nTicket: #254\nEOF`,
  ],
  [
    "a heredoc in a substitution",
    "git commit -m \"$(cat <<'EOF'\nFix it) and git commit again\nEOF\n)\"",
    `git commit -m "$(cat <<'EOF'\nFix it) and git commit again\nEOF\n)" ${TRAILER}`,
  ],
  ["an && chain", 'git add -A && git commit -m "x"', `git add -A && git commit -m "x" ${TRAILER}`],
  ["an || chain", 'git diff --quiet || git commit -am "x"', `git diff --quiet || git commit -am "x" ${TRAILER}`],
  ["a ; chain", 'git add -A; git commit -m "x"; git log -1', `git add -A; git commit -m "x" ${TRAILER}; git log -1`],
  ["-C", 'git -C "C:/work tree" commit -m x', `git -C "C:/work tree" commit -m x ${TRAILER}`],
  ["-c", "git -c user.name=Bot commit -m x", `git -c user.name=Bot commit -m x ${TRAILER}`],
  ["--amend", "git commit --amend --no-edit", `git commit --amend --no-edit ${TRAILER}`],
  ["an environment before git", "GIT_AUTHOR_NAME=Bot git commit -m x", `GIT_AUTHOR_NAME=Bot git commit -m x ${TRAILER}`],
  ["a subshell", '(cd sub && git commit -m "x")', `(cd sub && git commit -m "x" ${TRAILER})`],
  ["a redirect", "git commit -m x > out.txt 2>&1", `git commit -m x > out.txt 2>&1 ${TRAILER}`],
  ["a comment after it", "git commit -m x # done", `git commit -m x ${TRAILER} # done`],
  ["paths after --", "git commit -m x -- work.txt", `git commit -m x ${TRAILER} -- work.txt`],
  [
    "two commits",
    "git commit -m a && git commit --allow-empty -m b",
    `git commit -m a ${TRAILER} && git commit --allow-empty -m b ${TRAILER}`,
  ],
]) {
  test(`a commit given ${form} keeps its own text and gets the trailer after it`, async () => {
    // Act
    const got = await rewritten(command);

    // Assert
    assert.equal(got, expected);
  });
}

for (const [tool, trailer] of [
  ["Bash", (value) => `--trailer "${value}"`],
  ["PowerShell", (value) => `--trailer '${value}'`],
]) {
  test(`a ${tool} commit handed a ticket, with the credit shown, gains only trailers after its own text`, async () => {
    // Arrange
    const repo = await creditRepository("show");
    const command = 'git add -A && git commit -m "Fix the thing"';

    // Act
    const got = await rewritten(command, SESSION, tool, "#254", repo.dir);

    // Assert
    const added = ["Ticket: #254", `Co-Authored-By: ${CREDIT}`, `Skillworks-Session: ${SESSION}`].map(trailer);
    assert.equal(got, `${command} ${added.join(" ")}`);
  });
}

test("after the hook runs in a repo, its config holds the three rules, and a rule it held otherwise is replaced", async () => {
  // Arrange
  const repo = await repository();
  repo.git("config", "--local", "trailer.Ticket.ifExists", "addIfDifferent");

  // Act
  await rewritten("git commit -m x", SESSION, "Bash", "", repo.dir);

  // Assert
  const rules = ["Skillworks-Session", "Co-Authored-By", "Ticket"].map((key) =>
    repo.git("config", "--local", "--get", `trailer.${key}.ifExists`).trim(),
  );
  assert.deepEqual(rules, ["addIfDifferent", "addIfDifferent", "replace"]);
});

test("a commit whose cwd is no repo is still rewritten with its trailers", async () => {
  // Act
  const got = await rewritten("git commit -m x", SESSION, "Bash", "#254", temp);

  // Assert
  assert.equal(got, `git commit -m x --trailer "Ticket: #254" ${TRAILER}`);
});

test("a commit in a repo whose config stays locked is still rewritten with its trailers", async () => {
  // Arrange
  const repo = await repository();
  await writeFile(join(repo.dir, ".git", "config.lock"), "");

  // Act
  const got = await rewritten("git commit -m x", SESSION, "Bash", "", repo.dir);

  // Assert
  assert.equal(got, `git commit -m x ${TRAILER}`);
});

test("a rewrite keeps every other field of the tool input", async () => {
  // Act
  const answer = await answerTo("git commit -m x");

  // Assert
  assert.deepEqual(answer.updatedInput, { ...input("").tool_input, command: `git commit -m x ${TRAILER}` });
});

for (const [state, extra] of [
  ["on", { OTEL_EXPORTER_OTLP_ENDPOINT: "http://127.0.0.1:1", [TICKET_VARIABLE]: "" }],
  ["off", { OTEL_EXPORTER_OTLP_ENDPOINT: "", [TICKET_VARIABLE]: "" }],
]) {
  test(`a commit gets the trailer with telemetry ${state}`, async () => {
    // Act
    const ran = await hook(input("git commit -m x"), extra);

    // Assert
    assert.equal(ran.status, 0, ran.err);
    assert.equal(JSON.parse(ran.out).hookSpecificOutput.updatedInput.command, `git commit -m x ${TRAILER}`);
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
    const command = await rewritten(commandIn(repo), SESSION, "Bash", "", repo.dir);

    // Act
    repo.run(command);

    // Assert
    assert.deepEqual(sessions(repo), [SESSION]);
  });
}

// The hook never reads a message file, so a credit line typed there reaches the commit.
for (const [form, trailers] of [
  ["Ticket alone", ["Ticket: #254"]],
  ["Ticket and Co-Authored-By", ["Ticket: #254", "Co-Authored-By: Claude <noreply@anthropic.com>"]],
]) {
  test(`the trailer joins the block that holds ${form}`, async () => {
    // Arrange
    const repo = await repository();
    await writeFile(join(repo.dir, "message.txt"), `Fix the thing\n\nThe body.\n\n${trailers.join("\n")}\n`);
    const command = await rewritten("git add work.txt && git commit -F message.txt", SESSION, "Bash", "", repo.dir);

    // Act
    repo.run(command);

    // Assert
    const block = repo.git("log", "-1", "--format=%(trailers:only,unfold)").trim();
    assert.deepEqual(block.split("\n"), [...trailers, `Skillworks-Session: ${SESSION}`]);
  });
}

test("an amend by the same Session adds no second line, and one by a second Session adds one", async () => {
  // Arrange
  const repo = await repository();
  repo.run(await rewritten('git add -A && git commit -m "Fix the thing"', SESSION, "Bash", "", repo.dir));
  const amend = "git commit --amend --no-edit";

  // Act
  repo.run(await rewritten(amend, SESSION, "Bash", "", repo.dir));
  const afterSame = sessions(repo);
  repo.run(await rewritten(amend, SECOND_SESSION, "Bash", "", repo.dir));
  const afterSecond = sessions(repo);

  // Assert
  assert.deepEqual(afterSame, [SESSION]);
  assert.deepEqual(afterSecond, [SESSION, SECOND_SESSION]);
});

for (const ticket of ["#254", "7/2"]) {
  test(`git reads the Ticket ${ticket} the Session was handed from a Bash commit`, async () => {
    // Arrange
    const repo = await repository();
    const command = await rewritten('git add -A && git commit -m "Fix the thing"', SESSION, "Bash", ticket, repo.dir);

    // Act
    repo.run(command);

    // Assert
    assert.deepEqual(tickets(repo), [ticket]);
  });
}

test("a commit by a Session handed no ticket carries no Ticket from the hook", async () => {
  // Arrange
  const repo = await repository();
  const command = await rewritten('git add -A && git commit -m "Fix the thing"', SESSION, "Bash", "", repo.dir);

  // Act
  repo.run(command);

  // Assert
  assert.deepEqual(tickets(repo), []);
});

test("a Ticket typed in the trailer block is replaced by the one the Session was handed", async () => {
  // Arrange
  const repo = await repository();
  const message = "Fix the thing\n\nThe body.\n\nTicket: #1\nCo-Authored-By: Ada <ada@example.invalid>\n";
  await writeFile(join(repo.dir, "message.txt"), message);
  const command = await rewritten("git add work.txt && git commit -F message.txt", SESSION, "Bash", "#254", repo.dir);

  // Act
  repo.run(command);

  // Assert
  assert.deepEqual(tickets(repo), ["#254"]);
});

test("a Ticket stranded above a blank line still leaves a Ticket git reads", async () => {
  // Arrange
  const repo = await repository();
  const message = "Fix the thing\n\nTicket: #254\n\nCo-Authored-By: Ada <ada@example.invalid>\n";
  await writeFile(join(repo.dir, "message.txt"), message);
  const command = await rewritten("git add work.txt && git commit -F message.txt", SESSION, "Bash", "#254", repo.dir);

  // Act
  repo.run(command);

  // Assert
  assert.deepEqual(tickets(repo), ["#254"]);
});

test("an amend by the same Session handed a ticket adds no second Session line", async () => {
  // Arrange
  const repo = await repository();
  repo.run(await rewritten('git add -A && git commit -m "Fix the thing"', SESSION, "Bash", "#254", repo.dir));

  // Act
  repo.run(await rewritten("git commit --amend --no-edit", SESSION, "Bash", "#254", repo.dir));

  // Assert
  assert.deepEqual(sessions(repo), [SESSION]);
});

test("an amend by a second Session handed a ticket adds its line beside the first", async () => {
  // Arrange
  const repo = await repository();
  repo.run(await rewritten('git add -A && git commit -m "Fix the thing"', SESSION, "Bash", "#254", repo.dir));

  // Act
  repo.run(await rewritten("git commit --amend --no-edit", SECOND_SESSION, "Bash", "#254", repo.dir));

  // Assert
  assert.deepEqual(sessions(repo), [SESSION, SECOND_SESSION]);
});

test("a ticket the hook cannot write safely into a command is denied", async () => {
  // Act
  const answer = await answerTo("git commit -m x", SESSION, "Bash", '#1"; rm -rf ~; "');

  // Assert
  assert.equal(answer.permissionDecision, "deny");
});

test("git reads Claude's credit from a Bash commit when the team chose to show it", async () => {
  // Arrange
  const repo = await creditRepository("show");
  const command = await rewritten('git add -A && git commit -m "Fix the thing"', SESSION, "Bash", "", repo.dir);

  // Act
  repo.run(command);

  // Assert
  assert.deepEqual(credits(repo), [CREDIT]);
});

for (const [state, answer] of [
  ["chose to hide it", "hide"],
  ["gave no answer", undefined],
]) {
  test(`a commit carries no credit from the hook when the team ${state}`, async () => {
    // Arrange
    const repo = await creditRepository(answer);
    const command = await rewritten('git add -A && git commit -m "Fix the thing"', SESSION, "Bash", "", repo.dir);

    // Act
    repo.run(command);

    // Assert
    assert.deepEqual(credits(repo), []);
  });
}

test("a commit in a repository with no loop.json carries no credit from the hook", async () => {
  // Arrange
  const repo = await repository();
  const command = await rewritten('git add -A && git commit -m "Fix the thing"', SESSION, "Bash", "", repo.dir);

  // Act
  repo.run(command);

  // Assert
  assert.deepEqual(credits(repo), []);
});

test("an amend by the same Session with the credit shown adds no second credit line", async () => {
  // Arrange
  const repo = await creditRepository("show");
  repo.run(await rewritten('git add -A && git commit -m "Fix the thing"', SESSION, "Bash", "", repo.dir));

  // Act
  repo.run(await rewritten("git commit --amend --no-edit", SESSION, "Bash", "", repo.dir));

  // Assert
  assert.deepEqual(credits(repo), [CREDIT]);
});

for (const answer of ["show", "hide", undefined]) {
  test(`a person's Co-Authored-By line stays on the commit with ${answer ?? "no answer"}`, async () => {
    // Arrange
    const repo = await creditRepository(answer);
    const typed = 'git add -A && git commit -m "Fix the thing" -m "Co-Authored-By: Ada <ada@example.invalid>"';
    const command = await rewritten(typed, SESSION, "Bash", "", repo.dir);

    // Act
    repo.run(command);

    // Assert
    assert.ok(credits(repo).includes("Ada <ada@example.invalid>"), credits(repo).join("\n"));
  });
}

const TYPED_CREDITS = [
  [
    "Bash",
    "a heredoc",
    'git commit -m "$(cat <<\'EOF\'\nFix the thing\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nEOF\n)"',
  ],
  ["Bash", "a lower-case key", 'git commit -m "Fix the thing\n\nco-authored-by: Claude <noreply@anthropic.com>"'],
  ["Bash", "a message of its own", 'git commit -m "Fix the thing" -m "Co-Authored-By: Claude <noreply@anthropic.com>"'],
  ["Bash", "an ANSI-C string", "git commit -m $'Fix the thing\\n\\nCo-Authored-By: Claude <noreply@anthropic.com>'"],
  ["PowerShell", "an upper-case key", "git commit -m @'\nFix the thing\n\nCO-AUTHORED-BY: Claude <noreply@anthropic.com>\n'@"],
  ["PowerShell", "an escaped new line", 'git commit -m "Fix the thing`n`nCo-Authored-By: Claude <noreply@anthropic.com>"'],
];

for (const answer of ["show", "hide"]) {
  for (const [tool, form, command] of TYPED_CREDITS) {
    test(`a ${tool} commit holding a typed Claude credit line in ${form} is denied with ${answer}`, async () => {
      // Arrange
      const repo = await creditRepository(answer);

      // Act
      const got = await answerTo(command, SESSION, tool, "", repo.dir);

      // Assert
      assert.equal(got.permissionDecision, "deny");
      assert.match(got.permissionDecisionReason, /loop\.json/);
      assert.match(got.permissionDecisionReason, /remove the line and run the commit again/i);
      assert.equal(got.updatedInput, undefined);
    });
  }
}

for (const [tool, form, command] of TYPED_CREDITS) {
  test(`a ${tool} commit holding a typed Claude credit line in ${form} passes with no answer`, async () => {
    // Arrange
    const repo = await creditRepository(undefined);

    // Act
    const got = await answerTo(command, SESSION, tool, "", repo.dir);

    // Assert
    assert.ok(got.updatedInput);
  });
}

test("a typed Claude credit line in a command with no commit passes unchanged", async () => {
  // Arrange
  const repo = await creditRepository("show");

  // Act
  const got = await answerTo('echo "Co-Authored-By: Claude <noreply@anthropic.com>"', SESSION, "Bash", "", repo.dir);

  // Assert
  assert.equal(got, undefined);
});

for (const command of [
  "Get-ChildItem",
  "git status",
  "git log --grep commit",
  'Write-Output "commit"',
  "git log --oneline | Select-String commit",
  'Write-Output "git commit"',
  "git commit-tree HEAD^{tree} -m x",
  "npm test # then git commit",
  "<# git commit #> git status",
  "gh issue comment 254 --body 'run git commit'",
  "@'\ngit commit -m x\n'@ | Set-Content notes.txt",
  "pwsh -Command 'git log --grep commit'",
]) {
  test(`a PowerShell command with no git commit passes unchanged: ${command}`, async () => {
    // Act
    const answer = await answerTo(command, SESSION, "PowerShell");

    // Assert
    assert.equal(answer, undefined);
  });
}

for (const [form, command, expected] of [
  ["-m", 'git commit -m "Fix the thing"', `git commit -m "Fix the thing" ${PS_TRAILER}`],
  ["-F", "git commit -F message.txt", `git commit -F message.txt ${PS_TRAILER}`],
  [
    "a here-string message",
    "git commit -m @'\nFix (the) thing; and git commit again\n\nTicket: #254\n'@",
    `git commit -m @'\nFix (the) thing; and git commit again\n\nTicket: #254\n'@ ${PS_TRAILER}`,
  ],
  ["a here-string piped in", '@"\nFix it\n"@ | git commit -F -', `@"\nFix it\n"@ | git commit -F - ${PS_TRAILER}`],
  ["an && chain", 'git add -A && git commit -m "x"', `git add -A && git commit -m "x" ${PS_TRAILER}`],
  ["an || chain", "git diff --quiet || git commit -am 'x'", `git diff --quiet || git commit -am 'x' ${PS_TRAILER}`],
  ["a ; chain", 'git add -A; git commit -m "x"; git log -1', `git add -A; git commit -m "x" ${PS_TRAILER}; git log -1`],
  ["-C", 'git -C "C:/work tree" commit -m x', `git -C "C:/work tree" commit -m x ${PS_TRAILER}`],
  ["-c", "git -c user.name=Bot commit -m x", `git -c user.name=Bot commit -m x ${PS_TRAILER}`],
  ["--amend", "git commit --amend --no-edit", `git commit --amend --no-edit ${PS_TRAILER}`],
  ["the call operator", "& git commit -m x", `& git commit -m x ${PS_TRAILER}`],
  [
    "a quoted path to git.exe",
    "& 'C:\\Program Files\\Git\\cmd\\git.exe' commit -m x",
    `& 'C:\\Program Files\\Git\\cmd\\git.exe' commit -m x ${PS_TRAILER}`,
  ],
  ["an assignment", "$out = git commit -m x", `$out = git commit -m x ${PS_TRAILER}`],
  [
    "an if block",
    "if ($LASTEXITCODE -eq 0) { git commit -m x } else { Write-Output no }",
    `if ($LASTEXITCODE -eq 0) { git commit -m x ${PS_TRAILER} } else { Write-Output no }`,
  ],
  ["a line continued", "git `\n  commit -m x", `git \`\n  commit -m x ${PS_TRAILER}`],
  ["a redirect", "git commit -m x *> out.txt", `git commit -m x *> out.txt ${PS_TRAILER}`],
  ["paths after --", "git commit -m x -- work.txt", `git commit -m x ${PS_TRAILER} -- work.txt`],
  [
    "two commits",
    "git commit -m a; git commit --allow-empty -m b",
    `git commit -m a ${PS_TRAILER}; git commit --allow-empty -m b ${PS_TRAILER}`,
  ],
]) {
  test(`a PowerShell commit given ${form} keeps its own text and gets the trailer after it`, async () => {
    // Act
    const got = await rewritten(command, SESSION, "PowerShell");

    // Assert
    assert.equal(got, expected);
  });
}

for (const [form, command] of [
  ["pwsh -Command", 'pwsh -Command "git commit -m x"'],
  ["powershell -Command", "powershell -NoProfile -Command 'git add -A; git commit -m x'"],
  ["Invoke-Expression", "Invoke-Expression 'git commit -m x'"],
  ["iex", 'iex "git commit -m x"'],
  ["a here-string passed to Invoke-Expression", "Invoke-Expression @'\ngit commit -m x\n'@"],
  ["a string piped to Invoke-Expression", "'git commit -m x' | Invoke-Expression"],
  ["a variable handed to Invoke-Expression", "$c = 'git commit -m x'; Invoke-Expression $c"],
  ["a script block run by the call operator", "& { git commit -m x }"],
  ["a script block handed to Invoke-Command", "Invoke-Command -ScriptBlock { git commit -m x }"],
  ["a script block handed to ForEach-Object", "1 | ForEach-Object { git commit -m x }"],
  ["Start-Process", "Start-Process git -ArgumentList 'commit', '-m', 'x'"],
  ["cmd /c", 'cmd /c "git commit -m x"'],
  ["the stop-parsing token", "git --% commit -m x"],
  ["a chain beside a plain commit", "git commit -m a; pwsh -Command 'git commit -m b'"],
]) {
  test(`a PowerShell commit inside ${form} is denied with the plain-command reason`, async () => {
    // Act
    const answer = await answerTo(command, SESSION, "PowerShell");

    // Assert
    assert.equal(answer.permissionDecision, "deny");
    assert.match(answer.permissionDecisionReason, /Run `git commit` as a plain command of its own/);
    assert.equal(answer.updatedInput, undefined);
  });
}

test("a PowerShell commit with no Session id to write is denied", async () => {
  // Act
  const answer = await answerTo("git commit -m x", null, "PowerShell");

  // Assert
  assert.equal(answer.permissionDecision, "deny");
});

for (const [form, commandIn] of [
  ["-m", () => "git add -A; git commit -m 'Fix the thing'"],
  ["a here-string message", () => "git add -A\ngit commit -m @'\nFix (the) thing\n\nTicket: #254\n'@"],
  ["-C", (repo) => `git add -A && git -C "${repo.dir}" commit -m "Fix the thing"`],
]) {
  test(
    `git reads the Session back from a commit PowerShell made by the rewritten command, given ${form}`,
    { skip: NO_PWSH },
    async () => {
      // Arrange
      const repo = await repository();
      const command = await rewritten(commandIn(repo), SESSION, "PowerShell", "", repo.dir);

      // Act
      await repo.runPowerShell(command);

      // Assert
      assert.deepEqual(sessions(repo), [SESSION]);
    },
  );
}

for (const ticket of ["#254", "7/2"]) {
  test(`git reads the Ticket ${ticket} the Session was handed from a PowerShell commit`, { skip: NO_PWSH }, async () => {
    // Arrange
    const repo = await repository();
    const command = await rewritten("git add -A; git commit -m 'Fix the thing'", SESSION, "PowerShell", ticket, repo.dir);

    // Act
    await repo.runPowerShell(command);

    // Assert
    assert.deepEqual(tickets(repo), [ticket]);
  });
}

test("git reads Claude's credit from a PowerShell commit when the team chose to show it", { skip: NO_PWSH }, async () => {
  // Arrange
  const repo = await creditRepository("show");
  const command = await rewritten("git add -A; git commit -m 'Fix the thing'", SESSION, "PowerShell", "", repo.dir);

  // Act
  await repo.runPowerShell(command);

  // Assert
  assert.deepEqual(credits(repo), [CREDIT]);
});
