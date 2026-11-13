import { execFileSync } from "node:child_process";
import { mkdtemp, realpath, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

import { sidecarOf } from "../../../../../plugins/skillworks/scripts/sidecar/sidecar.mjs";

const SCRIPTS = join(import.meta.dirname, "..", "..", "..", "..", "..", "plugins", "skillworks", "scripts");

let temp;
let work;
let nested;

function git(where, ...args) {
  return execFileSync("git", ["-C", where, ...args], { encoding: "utf8" });
}

beforeEach(async () => {
  // The temporary folder can sit behind a link, and git names the folder it resolves to.
  temp = await realpath(await mkdtemp(join(tmpdir(), "sidecar-")));
  work = join(temp, "work");
  execFileSync("git", ["init", "--quiet", work]);
  git(work, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
    "commit", "--quiet", "--allow-empty", "-m", "Base");
  nested = join(work, ".spec-loop", "nested", "job");
  git(work, "worktree", "add", "--quiet", "-b", "job", nested);
});

afterEach(async () => {
  await rm(temp, { recursive: true, force: true });
});

function pythonSidecarOf(where) {
  const program = [
    "import sys",
    "sys.path.insert(0, sys.argv[1])",
    "from runner import Subprocess",
    "from sidecar.locator import sidecar_of",
    "sys.stdout.write(str(sidecar_of(Subprocess(), sys.argv[2])))",
  ].join("\n");
  return execFileSync("uv", ["run", "--no-project", "python", "-c", program, SCRIPTS, where],
    { encoding: "utf8" });
}

test("the locator names the folder beside the main checkout from a nested worktree", () => {
  assert.equal(resolve(sidecarOf(nested)), join(temp, "work-skillworks"));
});

test("the node and python locators name one folder from the main checkout and a nested worktree", () => {
  const found = new Set([work, nested].flatMap((where) =>
    [resolve(sidecarOf(where)), resolve(pythonSidecarOf(where))]));

  assert.deepEqual([...found], [join(temp, "work-skillworks")]);
});
