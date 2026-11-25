import { execFileSync } from "node:child_process";

// Git lists the main checkout first, so every worktree of one clone finds the same main checkout.
export function mainCheckoutOf(where) {
  // A hook speaks only through what it prints, so git's own complaint must not reach stderr.
  const listed = execFileSync("git", ["-C", where, "worktree", "list", "--porcelain"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });
  return listed.split("\n")[0].replace(/^worktree /, "").trimEnd();
}

export function sidecarOf(where) {
  return `${mainCheckoutOf(where)}-skillworks`;
}
