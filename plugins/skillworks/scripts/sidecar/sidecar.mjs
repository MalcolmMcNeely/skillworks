import { execFileSync } from "node:child_process";

// Git lists the main checkout first, so every worktree of one clone finds the same Sidecar.
export function sidecarOf(where) {
  const listed = execFileSync("git", ["-C", where, "worktree", "list", "--porcelain"], { encoding: "utf8" });
  const main = listed.split("\n")[0].replace(/^worktree /, "").trimEnd();
  return `${main}-skillworks`;
}
