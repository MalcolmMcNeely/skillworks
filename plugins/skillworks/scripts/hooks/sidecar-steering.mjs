// Claude Code reads CLAUDE.md only from the folders above a Session, and the Sidecar sits beside the repo, never above it.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { text } from "node:stream/consumers";
import { sidecarSteering } from "./steering-folder.mjs";

// Claude Code follows imports this many hops deep, so a rule nested past it loads in neither place.
const IMPORT_HOPS = 5;

const IMPORT = /^@(\S+)$/;

function expanded(sidecar, name, hops, seen) {
  if (seen.has(name)) return "";
  seen.add(name);
  let held;
  try {
    held = readFileSync(join(sidecar, name), "utf8");
  } catch {
    return "";
  }
  const imports = held.split(/\r?\n/).map((line) => IMPORT.exec(line.trim())?.[1]).filter(Boolean);
  const nested = hops === 0 ? [] : imports.map((imported) => expanded(sidecar, imported, hops - 1, seen));
  return [`## ${name}\n\n${held.trimEnd()}\n`, ...nested.filter(Boolean)].join("\n");
}

try {
  const payload = JSON.parse(await text(process.stdin));
  const sidecar = sidecarSteering(typeof payload.cwd === "string" ? payload.cwd : process.cwd());
  if (sidecar !== undefined) {
    const steering = expanded(sidecar, "CLAUDE.md", IMPORT_HOPS, new Set());
    const context =
      `Sidecar Steering is on. The Steering sits in the Sidecar at ${sidecar.replaceAll("\\", "/")}, and not in ` +
      "the repo. Read each Steering file with steering-file. The Sidecar's CLAUDE.md and each file it imports " +
      `follow, and they hold the team's rules.\n\n${steering}`;
    process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: context } }));
  }
} catch {
  // A Session must start even when the Sidecar cannot be read, and the rules then load from the repo as before.
}
