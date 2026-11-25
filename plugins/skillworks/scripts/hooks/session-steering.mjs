// Claude Code reads CLAUDE.md only from the folders above a Session, and the Sidecar sits beside the repo, never above it.

import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { text } from "node:stream/consumers";
import { loopFileInBoth, sidecarSteering } from "./steering-folder.mjs";
import { pullSteering } from "./steering-pull.mjs";

// Claude Code follows imports this many hops deep, so a rule nested past it loads in neither place.
const IMPORT_HOPS = 5;

// Claude Code reads an import with this pattern, so the two agree on what loads.
const IMPORT = /(?:^|(?<=\s))@((?:[^\s\\]|\\ )+)/gm;

const FENCE_OPEN = /^\s*(`{3,}|~{3,})/;

const CODE_SPAN = /(`+)(?:(?!\1)[\s\S])+?\1/g;

const ROOT_FILE = "CLAUDE.md";

function outsideCode(held) {
  const kept = [];
  let fence;
  for (const line of held.split(/\r?\n/)) {
    const opened = FENCE_OPEN.exec(line);
    if (fence === undefined && opened) fence = opened[1];
    else if (fence !== undefined && line.trim().startsWith(fence[0].repeat(fence.length))) fence = undefined;
    else if (fence === undefined) kept.push(line);
  }
  return kept.join("\n").replace(CODE_SPAN, " ");
}

function importsOf(held) {
  return [...outsideCode(held).matchAll(IMPORT)]
    .map((found) => found[1].replaceAll("\\ ", " ").split("#")[0])
    .filter(Boolean);
}

function shownPath(path, sidecar) {
  for (const [root, prefix] of [[sidecar, ""], [homedir(), "~/"]]) {
    const inside = relative(root, path);
    if (inside !== "" && !inside.startsWith("..") && !isAbsolute(inside)) return prefix + inside.replaceAll("\\", "/");
  }
  return path.replaceAll("\\", "/");
}

// Claude Code resolves an import from the folder of the file that holds it, and ~/ from the home folder.
function resolved(name, holder) {
  return name.startsWith("~/") ? resolve(homedir(), name.slice(2)) : resolve(dirname(holder), name);
}

function read(path) {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return undefined;
  }
}

function key(path) {
  return process.platform === "win32" ? path.toLowerCase() : path;
}

function expanded(path, sidecar, hops, seen) {
  if (seen.has(key(path))) return "";
  seen.add(key(path));
  const held = read(path);
  if (held === undefined) return "";
  const nested = hops === 0 ? [] : importsOf(held)
    .map((name) => expanded(resolved(name, path), sidecar, hops - 1, seen));
  return [`## ${shownPath(path, sidecar)}\n\n${held.trimEnd()}\n`, ...nested.filter(Boolean)].join("\n");
}

try {
  const payload = JSON.parse(await text(process.stdin));
  const where = typeof payload.cwd === "string" ? payload.cwd : process.cwd();
  const sidecar = sidecarSteering(where);
  if (sidecar !== undefined) {
    // Before the rules load, so every text in the Session comes from one commit.
    const pullFault = await pullSteering(sidecar);
    const steering = expanded(join(sidecar, ROOT_FILE), sidecar, IMPORT_HOPS, new Set());
    const inBoth = loopFileInBoth(where);
    const warnings = [
      pullFault === undefined ? undefined : `WARNING: ${pullFault}`,
      inBoth === undefined ? undefined : `WARNING: ${inBoth} Preflight stops every run until you do.`,
    ].filter(Boolean);
    const warningText = warnings.map((said) => `${said}\n\n`).join("");
    const context =
      `${warningText}Sidecar Steering is on. The Steering sits in the Sidecar at ${sidecar.replaceAll("\\", "/")}, and not in ` +
      "the repo. Read each Steering file with steering-file. The Sidecar's CLAUDE.md and each file it imports " +
      `follow, and they hold the team's rules.\n\n${steering}`;
    const answer = { hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: context } };
    // The context reaches only the model, and the person has to see that their Steering may be stale.
    if (pullFault !== undefined) answer.systemMessage = `WARNING: ${pullFault}`;
    process.stdout.write(JSON.stringify(answer));
  }
} catch {
  // A Session must start even when the Sidecar cannot be read, and the rules then load from the repo as before.
}
