// A commit hidden in a string is only ever read as text, so this spots one without parsing it.
export const COMMIT_IN_TEXT = /\bgit(?:\.exe)?(?:\s+-{1,2}[^\s'"]+(?:\s+[^\s'"-][^\s'"]*)?)*\s+commit\b/;

// These git options take their value as the next word, so that word is not the subcommand.
export const GIT_OPTIONS_WITH_VALUE = new Set(["-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"]);

export function baseName(value) {
  return value.split(/[\\/]/).pop().replace(/\.exe$/i, "").toLowerCase();
}
