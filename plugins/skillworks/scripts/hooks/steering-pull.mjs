import { execFileSync, spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { LOOP_FILE } from "./steering-folder.mjs";

// The driver pulls once for a whole run, so a Session of the run reads the commit the run holds.
export const LOOP_SESSION_VARIABLE = "SKILLWORKS_LOOP_SESSION";

const PULL_SECONDS_KEY = "steering-pull-seconds";

const DEFAULT_PULL_SECONDS = 30;

// Claude Code stops this hook at 300 seconds, so a pull held to 240 always stops first.
const MOST_PULL_SECONDS = 240;

// Preflight turns down any other value, and a Session must still start on one.
function pullSeconds(sidecar) {
  try {
    const held = JSON.parse(readFileSync(join(sidecar, LOOP_FILE), "utf8"))[PULL_SECONDS_KEY];
    return Number.isInteger(held) && held >= 1 && held <= MOST_PULL_SECONDS ? held : DEFAULT_PULL_SECONDS;
  } catch {
    return DEFAULT_PULL_SECONDS;
  }
}

function hasRemote(sidecar) {
  try {
    return execFileSync("git", ["-C", sidecar, "remote"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    }).trim() !== "";
  } catch {
    return false;
  }
}

// git hands a remote over https or ssh to a child of its own, and a child left alive would hold the pull open.
function stopAll(child) {
  try {
    if (process.platform === "win32") {
      execFileSync("taskkill", ["/pid", String(child.pid), "/t", "/f"], { stdio: "ignore", windowsHide: true });
    } else {
      process.kill(-child.pid, "SIGKILL");
    }
  } catch {
    child.kill("SIGKILL");
  }
}

function reasonIn(said) {
  const lines = said.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  return lines.find((line) => /^(fatal|error):/.test(line)) ?? lines.at(-1) ?? "git gave no reason";
}

function pulled(sidecar, seconds) {
  return new Promise((done) => {
    const child = spawn("git", ["-C", sidecar, "pull", "--ff-only", "--quiet"], {
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
      detached: process.platform !== "win32",
      env: { ...process.env, GIT_TERMINAL_PROMPT: "0", GCM_INTERACTIVE: "never" },
    });
    let said = "";
    child.stdout.on("data", (chunk) => (said += chunk));
    child.stderr.on("data", (chunk) => (said += chunk));
    const finish = (reason) => {
      clearTimeout(limit);
      child.stdout.destroy();
      child.stderr.destroy();
      done(reason);
    };
    const limit = setTimeout(() => {
      stopAll(child);
      finish(`ran past its limit of ${seconds} ${seconds === 1 ? "second" : "seconds"}`);
    }, seconds * 1000);
    child.on("error", (error) => finish(`could not start git: ${error.message}`));
    child.on("exit", (status) => finish(status === 0 ? undefined : `failed: ${reasonIn(said)}`));
  });
}

// One warning and never a stop, because a network fault must not keep a person from their work.
export async function pullSteering(sidecar) {
  if (process.env[LOOP_SESSION_VARIABLE] || !hasRemote(sidecar)) return undefined;
  const reason = await pulled(sidecar, pullSeconds(sidecar));
  if (reason === undefined) return undefined;
  return `the pull of the Steering repo into the Sidecar ${reason}. The Steering files on disk are read.`;
}
