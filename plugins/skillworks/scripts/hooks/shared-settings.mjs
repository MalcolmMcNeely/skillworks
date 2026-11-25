import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { mainCheckoutOf } from "../sidecar/sidecar.mjs";

const SHARED_SETTINGS_FILE = ".claude/settings.json";

// The developer's own Sessions run in the main checkout and never read the Sidecar's settings file.
const LOCAL_SETTINGS_FILE = ".claude/settings.local.json";

// A member's "always allow" clicks land in these lists, so the team's entries join them and replace none.
const JOINED_LISTS = ["allow", "deny"];

export function sharedSettingsText(sidecar) {
  try {
    return readFileSync(join(sidecar, SHARED_SETTINGS_FILE), "utf8");
  } catch {
    return undefined;
  }
}

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function joined(local, shared) {
  return [...local, ...shared.filter((entry) => !local.includes(entry))];
}

// Nested objects merge key by key, so a key only the local file holds stays.
function merged(local, shared, path = []) {
  const result = { ...local };
  for (const [key, value] of Object.entries(shared)) {
    const held = local[key];
    if (isObject(held) && isObject(value)) {
      result[key] = merged(held, value, [...path, key]);
    } else if (path.join(".") === "permissions" && JOINED_LISTS.includes(key) && Array.isArray(held) && Array.isArray(value)) {
      result[key] = joined(held, value);
    } else {
      result[key] = value;
    }
  }
  return result;
}

function localSettings(path) {
  let text;
  try {
    text = readFileSync(path, "utf8");
  } catch {
    return {};
  }
  const held = JSON.parse(text);
  if (!isObject(held)) throw new Error("it does not hold a JSON object");
  return held;
}

// Claude Code reads its settings once when a Session starts, so the Session that merged them runs on the old ones.
export function mergeSharedSettings(where, sidecar) {
  const localPath = join(mainCheckoutOf(where), LOCAL_SETTINGS_FILE);
  try {
    const shared = JSON.parse(sharedSettingsText(sidecar));
    if (!isObject(shared)) throw new Error(`the Sidecar's ${SHARED_SETTINGS_FILE} does not hold a JSON object`);
    const result = merged(localSettings(localPath), shared);
    mkdirSync(dirname(localPath), { recursive: true });
    writeFileSync(localPath, `${JSON.stringify(result, null, 2)}\n`);
  } catch (error) {
    return {
      warning: `the team's shared settings changed in the pull, and could not be merged into ` +
        `${LOCAL_SETTINGS_FILE} in the main checkout: ${error.message}. Nothing was written.`,
    };
  }
  return {
    said: `The team's shared settings changed in the pull, and were merged into ${LOCAL_SETTINGS_FILE} ` +
      "in the main checkout. The change applies from the next Session.",
  };
}
