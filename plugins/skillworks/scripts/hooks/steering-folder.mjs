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

export function steeringRoot(where) {
  return sidecarSteering(where) ?? where;
}
