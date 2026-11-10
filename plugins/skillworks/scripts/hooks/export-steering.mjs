// An Export branch holds no Steering, so the CLAUDE.md Claude Code loads there carries no rules and no Tracker.

import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { join, posix } from "node:path";
import { text } from "node:stream/consumers";
import { promisify } from "node:util";

// Read as the last fetch left it and never fetched, so a session starts offline and with no wait on the remote.
const STEERING_REF = "refs/remotes/origin/skillworks/steering";

const LINE = "This branch holds no Steering. Read each path under `docs/agents/` with `steering-file <path>`.";

// Claude Code follows imports this many hops deep and no deeper.
const MAX_HOPS = 5;

const run = promisify(execFile);

try {
  const payload = JSON.parse(await text(process.stdin));
  const loaded = await steeringFor(payload.cwd ?? process.cwd());
  if (loaded) {
    process.stdout.write(
      JSON.stringify({ hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: loaded } }),
    );
  }
} catch {
  // A session must still start when its Steering cannot be read.
}

async function steeringFor(cwd) {
  const git = async (...args) => (await run("git", ["-C", cwd, ...args], { maxBuffer: 16 * 1024 * 1024 })).stdout;
  const root = (await git("rev-parse", "--show-toplevel")).trim();
  if (existsSync(join(root, "docs", "agents", "loop.json"))) return undefined;
  try {
    await git("rev-parse", "--verify", "--quiet", `${STEERING_REF}^{commit}`);
  } catch {
    return undefined;
  }
  const read = async (path) => {
    try {
      return await git("show", `${STEERING_REF}:${path}`);
    } catch {
      return undefined;
    }
  };
  const files = [];
  await load("CLAUDE.md", 0, read, files, new Set());
  if (files.length === 0) return undefined;
  return [
    ...files.map(({ path, content }) => `Contents of ${path}, from origin/skillworks/steering:\n\n${content}`),
    LINE,
  ].join("\n\n");
}

async function load(path, hops, read, files, seen) {
  if (seen.has(path)) return;
  seen.add(path);
  const content = await read(path);
  if (content === undefined) return;
  files.push({ path, content });
  if (hops >= MAX_HOPS) return;
  for (const address of importsOf(content)) {
    const resolved = posix.normalize(posix.join(posix.dirname(path), address));
    // A home path or one outside the repo cannot be on the Steering branch.
    if (resolved.startsWith("../") || posix.isAbsolute(address) || address.startsWith("~")) continue;
    await load(resolved, hops + 1, read, files, seen);
  }
}

// Claude Code reads no import inside a code block or a code span, so neither is read here.
function importsOf(content) {
  const prose = content.replace(/^(```|~~~)[^\n]*\n[\s\S]*?^\1[^\n]*$/gm, "").replace(/`[^`\n]*`/g, "");
  return [...prose.matchAll(/(?:^|\s)@([^\s]+)/g)].map((match) => match[1]);
}
