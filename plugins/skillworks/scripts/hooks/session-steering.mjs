// Claude Code reads CLAUDE.md only from the folders above a Session, and the Sidecar sits beside the repo, never above it.
// A developer's remote Steering sits in no folder at all, so its CLAUDE.md loads from here too.

import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, isAbsolute, join, posix, relative, resolve } from "node:path";
import { text } from "node:stream/consumers";
import { loopFileInBoth, sidecarSteering } from "./steering-folder.mjs";

// Claude Code follows imports this many hops deep, so a rule nested past it loads in neither place.
const IMPORT_HOPS = 5;

// Claude Code reads an import with this pattern, so the two agree on what loads.
const IMPORT = /(?:^|(?<=\s))@((?:[^\s\\]|\\ )+)/gm;

const FENCE_OPEN = /^\s*(`{3,}|~{3,})/;

const CODE_SPAN = /(`+)(?:(?!\1)[\s\S])+?\1/g;

const SCRIPTS = resolve(import.meta.dirname, "..");

const REMOTE_SETTINGS = join(".skillworks", "remote-steering.json");

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
    if (root === undefined) continue;
    const inside = relative(root, path);
    if (inside !== "" && !inside.startsWith("..") && !isAbsolute(inside)) return prefix + inside.replaceAll("\\", "/");
  }
  return path.replaceAll("\\", "/");
}

// Claude Code resolves an import from the folder of the file that holds it, and ~/ from the home folder.
function resolved(name, holder) {
  return name.startsWith("~/") ? resolve(homedir(), name.slice(2)) : resolve(dirname(holder), name);
}

function onDisk(sidecar) {
  const disk = {
    key: (path) => "disk:" + (process.platform === "win32" ? path.toLowerCase() : path),
    read(path) {
      try {
        return readFileSync(path, "utf8");
      } catch {
        return undefined;
      }
    },
    imported: (name, holder) => ({ reader: disk, path: resolved(name, holder) }),
    shown: (path) => shownPath(path, sidecar),
  };
  return disk;
}

// A remote import resolves inside the remote's own tree, and ~/ or an absolute path still means this machine.
function inRemote(label, texts) {
  const remote = {
    key: (path) => "remote:" + path,
    read: (path) => texts.get(path) ?? undefined,
    imported(name, holder) {
      if (name.startsWith("~/") || isAbsolute(name)) return { reader: onDisk(undefined), path: resolved(name, holder) };
      const path = posix.normalize(posix.join(posix.dirname(holder), name));
      return path === ".." || path.startsWith("../") ? undefined : { reader: remote, path };
    },
    shown: (path) => `[${label}] ${path}`,
  };
  return remote;
}

function expanded(reader, path, hops, seen) {
  const key = reader.key(path);
  if (seen.has(key)) return "";
  seen.add(key);
  const held = reader.read(path);
  if (held === undefined) return "";
  const nested = hops === 0 ? [] : importsOf(held)
    .map((name) => reader.imported(name, path))
    .filter(Boolean)
    .map((found) => expanded(found.reader, found.path, hops - 1, seen));
  return [`## ${reader.shown(path)}\n\n${held.trimEnd()}\n`, ...nested.filter(Boolean)].join("\n");
}

// steering-file's own code finds the remote and the commit this Session holds, so the two never read different text.
function remoteFiles(where, session, paths) {
  const answer = execFileSync(
    "uv",
    ["run", "--no-project", "--quiet", "--with", "filelock>=3.16", "python", "-m", "hooks.remote_text",
      where, session, ...paths],
    { cwd: SCRIPTS, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], windowsHide: true },
  );
  return JSON.parse(answer).remote;
}

function remoteSteering(where, session, seen) {
  // Without this file no repo reads a remote, so a Session there starts no Python at all.
  if (!existsSync(join(homedir(), REMOTE_SETTINGS))) return undefined;
  let found;
  try {
    found = remoteFiles(where, session, [ROOT_FILE]);
  } catch (failed) {
    const said = String(failed.stderr ?? "").trim().replace(/^FAIL\s+/, "");
    return said === "" ? undefined : { said: `WARNING: ${said}\n\n` };
  }
  if (found === null) return undefined;
  const texts = new Map(Object.entries(found.files));
  const reader = inRemote(found.label, texts);
  // Each hop asks for every file it imports at once, so a Session pays for one Python start per hop and not per file.
  let reached = [ROOT_FILE];
  for (let hop = 0; hop < IMPORT_HOPS && reached.length > 0; hop++) {
    const wanted = [...new Set(reached.flatMap((path) => importsOf(texts.get(path) ?? "")
      .map((name) => reader.imported(name, path))
      .filter((next) => next?.reader === reader && !texts.has(next.path))
      .map((next) => next.path)))];
    if (wanted.length > 0) {
      for (const [path, held] of Object.entries(remoteFiles(where, session, wanted).files)) texts.set(path, held);
    }
    reached = wanted;
  }
  const warning = found.warning ? `WARNING: ${found.warning}\n\n` : "";
  const steering = expanded(reader, ROOT_FILE, IMPORT_HOPS, seen);
  return {
    said: `${warning}Remote Steering is on. Your remote Steering at ${found.label} adds to this repo's Steering, and ` +
      "steering-file reads it too. Its CLAUDE.md and each file it imports follow.\n\n" + steering,
  };
}

try {
  const payload = JSON.parse(await text(process.stdin));
  const where = typeof payload.cwd === "string" ? payload.cwd : process.cwd();
  const session = typeof payload.session_id === "string" ? payload.session_id : "";
  const seen = new Set();
  const parts = [];
  const sidecar = sidecarSteering(where);
  if (sidecar !== undefined) {
    const steering = expanded(onDisk(sidecar), join(sidecar, ROOT_FILE), IMPORT_HOPS, seen);
    const inBoth = loopFileInBoth(where);
    const warning = inBoth === undefined ? "" : `WARNING: ${inBoth} Preflight stops every run until you do.\n\n`;
    parts.push(
      `${warning}Sidecar Steering is on. The Steering sits in the Sidecar at ${sidecar.replaceAll("\\", "/")}, and not in ` +
      "the repo. Read each Steering file with steering-file. The Sidecar's CLAUDE.md and each file it imports " +
      `follow, and they hold the team's rules.\n\n${steering}`);
  }
  let remote;
  try {
    remote = remoteSteering(where, session, seen);
  } catch {
    // The Sidecar's rules must still load when the remote cannot be read past its first file.
  }
  if (remote !== undefined) parts.push(remote.said);
  if (parts.length > 0) {
    const context = parts.join("\n");
    process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: context } }));
  }
} catch {
  // A Session must start even when the Sidecar cannot be read, and the rules then load from the repo as before.
}
