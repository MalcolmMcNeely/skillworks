// Git places a --trailer in the message's own trailer block, and its default for an existing trailer adds no line equal to its neighbour.

import { text } from "node:stream/consumers";
import { baseName, COMMIT_IN_TEXT, GIT_OPTIONS_WITH_VALUE } from "./git-grammar.mjs";
import { powerShellCommits } from "./powershell-commits.mjs";

const KEY = "Skillworks-Session";

const PLAIN =
  "Run `git commit` as a plain command of its own, not inside a shell string, eval, backticks or another program, " +
  `so the ${KEY} trailer can be added to it.`;

const PLAIN_POWERSHELL =
  "Run `git commit` as a plain command of its own, not inside a script block, Invoke-Expression, a string handed " +
  `to pwsh -Command, powershell -Command or another program, so the ${KEY} trailer can be added to it.`;

// Each of these runs a command it is handed as words or as a string, which the hook cannot rewrite in place.
const RUNS_ANOTHER = new Set([
  "bash", "sh", "zsh", "dash", "ksh", "fish", "eval", "exec", "command", "env", "sudo", "su", "xargs",
  "nohup", "timeout", "nice", "watch", "find", "pwsh", "powershell", "cmd",
]);

// Bash reads these before the command's name, so the name is the word after them.
const LEADING_KEYWORDS = new Set(["{", "!", "if", "then", "else", "elif", "do", "while", "until", "time"]);

const OPERATORS = ["&&", "||", ";;", ";", "|&", "|", "&"];

const REDIRECT = /^\d*(?:<<<|<<-|<<|&>>|&>|>>|>&|<&|<>|>\||>|<)/;

function answer(output) {
  process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: "PreToolUse", ...output } }));
}

function judge(source, tool, sessionId) {
  const powerShell = tool === "PowerShell";
  const { ends, hidden } = powerShell ? powerShellCommits(source) : bashCommits(source);
  if (hidden) return { deny: powerShell ? PLAIN_POWERSHELL : PLAIN };
  if (ends.length === 0) return {};
  if (typeof sessionId !== "string" || !/^[A-Za-z0-9-]+$/.test(sessionId)) {
    return { deny: `The hook was handed no Session id it can write, so it cannot add the ${KEY} trailer.` };
  }
  const trailer = powerShell ? `'${KEY}: ${sessionId}'` : `"${KEY}: ${sessionId}"`;
  let rewritten = source;
  for (const end of ends.sort((a, b) => b - a)) {
    rewritten = `${rewritten.slice(0, end)} --trailer ${trailer}${rewritten.slice(end)}`;
  }
  return { command: rewritten };
}

function bashCommits(source) {
  const ends = [];
  for (const words of allCommands(new Scanner(source).list(false))) {
    const at = commitWord(words);
    if (at) ends.push(at.end);
    else if (hidesCommit(words)) return { ends, hidden: true };
  }
  return { ends, hidden: false };
}

function allCommands(commands) {
  return commands.flatMap((words) => [words, ...words.flatMap((word) => allCommands(word.inner))]);
}

function commitWord(words) {
  const at = nameIndex(words);
  if (at < 0 || !isGit(words[at])) return undefined;
  let i = at + 1;
  while (i < words.length) {
    const word = words[i];
    if (word.redirect) {
      i += 1;
    } else if (GIT_OPTIONS_WITH_VALUE.has(word.value)) {
      i += 2;
    } else if (word.value.startsWith("-")) {
      i += 1;
    } else {
      return word.value === "commit" && !word.dynamic ? word : undefined;
    }
  }
  return undefined;
}

function hidesCommit(words) {
  if (words.some((word) => word.ticks && COMMIT_IN_TEXT.test(word.raw))) return true;
  const at = nameIndex(words);
  if (at < 0 || !RUNS_ANOTHER.has(baseName(words[at].value))) return false;
  return COMMIT_IN_TEXT.test(words.slice(at).map((word) => word.raw).join(" "));
}

function nameIndex(words) {
  return words.findIndex(
    (word) => !word.redirect && !LEADING_KEYWORDS.has(word.raw) && !/^[A-Za-z_][A-Za-z0-9_]*\+?=/.test(word.raw),
  );
}

function isGit(word) {
  return !word.dynamic && baseName(word.value) === "git";
}

// Only enough of bash's grammar to bound each simple command's words, heredocs and substitutions included.
class Scanner {
  constructor(source) {
    this.source = source;
    this.at = 0;
    this.heredocs = [];
  }

  list(inSubstitution) {
    const commands = [];
    let words = [];
    let depth = 0;
    const end = () => {
      if (words.length > 0) commands.push(words);
      words = [];
    };
    while (this.at < this.source.length) {
      this.skipBlanks();
      if (this.at >= this.source.length) break;
      const c = this.source[this.at];
      if (c === ")") {
        this.at += 1;
        end();
        if (depth > 0) depth -= 1;
        else if (inSubstitution) return commands;
        continue;
      }
      if (c === "(") {
        this.at += 1;
        end();
        depth += 1;
        continue;
      }
      if (c === "\n") {
        this.at += 1;
        end();
        this.readHeredocs();
        continue;
      }
      if (c === "#") {
        while (this.at < this.source.length && this.source[this.at] !== "\n") this.at += 1;
        continue;
      }
      // Read before the operators, so &> is a redirect and not a command sent to the background.
      const redirect = REDIRECT.exec(this.source.slice(this.at));
      if (redirect) {
        this.at += redirect[0].length;
        this.skipBlanks();
        const target = { ...this.word(), redirect: true };
        const heredoc = /<<-?$/.exec(redirect[0]);
        if (heredoc) this.heredocs.push({ delimiter: target.value, tabs: heredoc[0] === "<<-" });
        words.push(target);
        continue;
      }
      const operator = OPERATORS.find((op) => this.source.startsWith(op, this.at));
      if (operator) {
        this.at += operator.length;
        end();
        continue;
      }
      words.push(this.word());
    }
    end();
    return commands;
  }

  skipBlanks() {
    while (this.at < this.source.length) {
      const c = this.source[this.at];
      if (c === " " || c === "\t" || c === "\r") this.at += 1;
      else if (c === "\\" && this.source[this.at + 1] === "\n") this.at += 2;
      else break;
    }
  }

  readHeredocs() {
    for (const { delimiter, tabs } of this.heredocs) {
      while (this.at < this.source.length) {
        let stop = this.source.indexOf("\n", this.at);
        if (stop < 0) stop = this.source.length;
        const line = this.source.slice(this.at, stop).replace(/\r$/, "");
        this.at = Math.min(stop + 1, this.source.length);
        if ((tabs ? line.replace(/^\t+/, "") : line) === delimiter) break;
      }
    }
    this.heredocs = [];
  }

  word() {
    const start = this.at;
    const word = { value: "", inner: [], dynamic: false, ticks: false };
    const s = this.source;
    while (this.at < s.length) {
      const c = s[this.at];
      if (" \t\r\n;&|()<>".includes(c)) break;
      if (c === "\\") {
        if (s[this.at + 1] !== "\n") word.value += s[this.at + 1] ?? "";
        this.at += 2;
      } else if (c === "'") {
        const close = s.indexOf("'", this.at + 1);
        const stop = close < 0 ? s.length : close;
        word.value += s.slice(this.at + 1, stop);
        this.at = stop + 1;
      } else if (c === '"') {
        this.at += 1;
        this.doubleQuoted(word);
      } else if (c === "$" || c === "`") {
        this.expansion(word);
      } else {
        word.value += c;
        this.at += 1;
      }
    }
    return { ...word, start, end: this.at, raw: s.slice(start, this.at) };
  }

  doubleQuoted(word) {
    const s = this.source;
    while (this.at < s.length && s[this.at] !== '"') {
      const c = s[this.at];
      if (c === "\\" && '$`"\\\n'.includes(s[this.at + 1])) {
        word.value += s[this.at + 1];
        this.at += 2;
      } else if (c === "$" || c === "`") {
        this.expansion(word);
      } else {
        word.value += c;
        this.at += 1;
      }
    }
    this.at += 1;
  }

  expansion(word) {
    const s = this.source;
    if (s[this.at] === "`") {
      let i = this.at + 1;
      while (i < s.length && s[i] !== "`") i += s[i] === "\\" ? 2 : 1;
      word.dynamic = true;
      word.ticks = true;
      this.at = i + 1;
    } else if (s.startsWith("$((", this.at)) {
      this.at = this.matching(this.at + 1, "(", ")");
      word.dynamic = true;
    } else if (s.startsWith("$(", this.at)) {
      this.at += 2;
      word.inner.push(...this.list(true));
      word.dynamic = true;
    } else if (s.startsWith("${", this.at)) {
      this.at = this.matching(this.at + 1, "{", "}");
      word.dynamic = true;
    } else {
      word.value += "$";
      this.at += 1;
      if (/[A-Za-z_0-9@*#?$!-]/.test(s[this.at] ?? "")) word.dynamic = true;
    }
  }

  matching(open, opening, closing) {
    let depth = 0;
    for (let i = open; i < this.source.length; i += 1) {
      if (this.source[i] === opening) depth += 1;
      else if (this.source[i] === closing && --depth === 0) return i + 1;
    }
    return this.source.length;
  }
}

const payload = JSON.parse(await text(process.stdin));
const command = payload.tool_input?.command;
if (typeof command !== "string") process.exit(0);

let verdict;
try {
  verdict = judge(command, payload.tool_name, payload.session_id);
} catch {
  // An unreadable command may still hold a commit, and a commit without the trailer is the miss this hook prevents.
  verdict = COMMIT_IN_TEXT.test(command) ? { deny: PLAIN } : {};
}

if (verdict.deny) {
  answer({ permissionDecision: "deny", permissionDecisionReason: verdict.deny });
} else if (verdict.command !== undefined) {
  // No decision is given, so the rewritten command still goes through the permissions the user set.
  answer({ updatedInput: { ...payload.tool_input, command: verdict.command } });
}
