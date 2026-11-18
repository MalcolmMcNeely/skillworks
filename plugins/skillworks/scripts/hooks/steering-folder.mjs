import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { sidecarOf } from "../sidecar/sidecar.mjs";

// Every hook builds its Steering paths from this one name, so the folder moves in one line.
export const STEERING_FOLDER = "docs/skillworks";

export const LOOP_FILE = `${STEERING_FOLDER}/loop.json`;

// The fact turns the mode on and no setting does, so a setting can never disagree with where the Steering sits.
export function sidecarSteering(where) {
  try {
    const sidecar = sidecarOf(where);
    return existsSync(join(sidecar, LOOP_FILE)) ? sidecar : undefined;
  } catch {
    return undefined;
  }
}

function repoTop(where) {
  // A hook speaks only through what it prints, so git's own complaint must not reach stderr.
  return execFileSync("git", ["-C", where, "rev-parse", "--show-toplevel"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  }).trim();
}

// Neither copy may win, because the one that won would hide the newer edits in the other.
export function loopFileInBoth(where) {
  const sidecar = sidecarSteering(where);
  if (sidecar === undefined) return undefined;
  let repoCopy;
  try {
    repoCopy = join(repoTop(where), LOOP_FILE);
  } catch {
    return undefined;
  }
  if (!existsSync(repoCopy)) return undefined;
  const copies = [repoCopy, join(sidecar, LOOP_FILE)].map((path) => path.replaceAll("\\", "/"));
  return `both the repo and the Sidecar hold ${LOOP_FILE}, so neither may win: ${copies[0]} and ${copies[1]}. ` +
    "Remove one of the two.";
}

export function steeringRoot(where) {
  return sidecarSteering(where) ?? where;
}
