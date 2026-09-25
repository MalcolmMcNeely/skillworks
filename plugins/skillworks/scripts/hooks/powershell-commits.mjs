import { baseName, COMMIT_IN_TEXT, GIT_OPTIONS_WITH_VALUE } from "./git-grammar.mjs";

// Each of these runs a command it is handed as a string or as words, which the hook cannot rewrite in place.
const RUNS_ANOTHER = new Set([
  "pwsh", "powershell", "cmd", "bash", "sh", "wsl", "invoke-expression", "iex", "invoke-command", "icm",
  "start-process", "saps", "start", "start-job", "sajb", "start-threadjob", "env", "xargs", "sudo",
]);

// A block after one of these runs where it stands, so a commit in it is as plain as one outside it.
const STATEMENT_KEYWORDS = new Set([
  "if", "elseif", "else", "foreach", "for", "while", "do", "until", "try", "catch", "finally", "switch",
]);

const ASSIGNMENT = /^(?:[-+*/%]|\?\?)?=$/;

const REDIRECT = /^(?:[1-6*]?>&[12]|[1-6*]?>>|[1-6*]?>|<)/;

const STOPPED = { stopped: true };

export function powerShellCommits(source) {
  const scanner = new Scanner(source);
  const ends = [];
  let hidden = false;
  let runsAnother = false;
  const walk = (pipelines, inScriptBlock) => {
    for (const pipeline of pipelines) {
      if (hidesCommit(pipeline)) hidden = true;
      for (const words of pipeline) {
        if (runs(words)) runsAnother = true;
        const at = commitWord(words);
        if (at === STOPPED || (at && inScriptBlock)) hidden = true;
        else if (at) ends.push(at.end);
        for (const word of words) walk(word.inner, inScriptBlock || word.scriptBlock);
      }
    }
  };
  walk(scanner.list(undefined), false);
  // A string reaches such a program through a variable as easily as in place, so one puts every string in doubt.
  if (runsAnother && scanner.strings.some((text) => COMMIT_IN_TEXT.test(unquoted(text)))) hidden = true;
  return { ends, hidden };
}

function commitWord(words) {
  const at = nameIndex(words);
  if (at < 0 || words[at].dynamic || baseName(words[at].value) !== "git") return undefined;
  let i = at + 1;
  while (i < words.length) {
    const word = words[i];
    if (word.stopParsing) {
      return STOPPED;
    } else if (word.redirect) {
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

function hidesCommit(pipeline) {
  if (!pipeline.some(runs)) return false;
  return COMMIT_IN_TEXT.test(unquoted(pipeline.flat().map((word) => word.raw).join(" ")));
}

function runs(words) {
  const at = nameIndex(words);
  return at >= 0 && RUNS_ANOTHER.has(baseName(words[at].value));
}

// Start-Process takes git's words as a quoted list, which reads as a plain command once the quotes go.
function unquoted(text) {
  return text.replace(/['",`]/g, " ");
}

function nameIndex(words) {
  let at = 0;
  const assignment = words.findIndex((word) => ASSIGNMENT.test(word.raw));
  if (assignment > 0 && words.slice(0, assignment).every((word) => /^[$[]/.test(word.raw))) at = assignment + 1;
  while (at < words.length && (words[at].redirect || words[at].raw === "&" || words[at].raw === ".")) at += 1;
  return at < words.length ? at : -1;
}

// Only enough of PowerShell's grammar to bound each command's words, here-strings and blocks included.
class Scanner {
  constructor(source) {
    this.source = source;
    this.at = 0;
    this.strings = [];
  }

  list(close) {
    const s = this.source;
    const pipelines = [];
    let pipeline = [];
    let words = [];
    const endCommand = () => {
      if (words.length > 0) pipeline.push(words);
      words = [];
    };
    const endPipeline = () => {
      endCommand();
      if (pipeline.length > 0) pipelines.push(pipeline);
      pipeline = [];
    };
    while (this.at < s.length) {
      this.skipBlanks();
      if (this.at >= s.length) break;
      const c = s[this.at];
      const start = this.at;
      if (c === close) {
        this.at += 1;
        endPipeline();
        return pipelines;
      }
      if (c === ")" || c === "}" || c === "\n" || c === ";") {
        this.at += 1;
        endPipeline();
        continue;
      }
      if (s.startsWith("<#", this.at)) {
        const stop = s.indexOf("#>", this.at + 2);
        this.at = stop < 0 ? s.length : stop + 2;
        continue;
      }
      if (c === "#") {
        while (this.at < s.length && s[this.at] !== "\n") this.at += 1;
        continue;
      }
      if (s.startsWith("&&", this.at) || s.startsWith("||", this.at)) {
        this.at += 2;
        endPipeline();
        continue;
      }
      if (c === "|") {
        this.at += 1;
        endCommand();
        continue;
      }
      // A lone & opens a command as the call operator, and ends one as a background job.
      if (c === "&") {
        this.at += 1;
        if (words.length === 0) words.push(this.made(start, { value: "&" }));
        else endPipeline();
        continue;
      }
      const redirect = REDIRECT.exec(s.slice(this.at));
      if (redirect) {
        this.at += redirect[0].length;
        this.skipBlanks();
        if (!redirect[0].includes("&") && this.at < s.length) words.push({ ...this.word(), redirect: true });
        continue;
      }
      if (c === "{") {
        const statement = words.length > 0 && STATEMENT_KEYWORDS.has(words[0].value.toLowerCase());
        this.at += 1;
        const inner = this.list("}");
        words.push(this.made(start, { inner, dynamic: true, scriptBlock: !statement }));
        if (statement) endPipeline();
        continue;
      }
      words.push(this.word());
      if (this.at === start) this.at += 1;
    }
    endPipeline();
    return pipelines;
  }

  made(start, fields) {
    return { value: "", inner: [], dynamic: false, ...fields, start, end: this.at, raw: this.source.slice(start, this.at) };
  }

  skipBlanks() {
    const s = this.source;
    while (this.at < s.length) {
      const c = s[this.at];
      if (c === " " || c === "\t" || c === "\r") this.at += 1;
      else if (c === "`" && s[this.at + 1] === "\n") this.at += 2;
      else if (c === "`" && s[this.at + 1] === "\r" && s[this.at + 2] === "\n") this.at += 3;
      else break;
    }
  }

  word() {
    const s = this.source;
    const start = this.at;
    const word = { value: "", inner: [], dynamic: false };
    const hereString = /^@(['"])[ \t]*\r?\n/.exec(s.slice(this.at));
    if (hereString) {
      this.at += hereString[0].length;
      if (hereString[1] === "'") this.literalHereString(word);
      else this.expandable(word, true);
      return this.made(start, word);
    }
    // After --% PowerShell hands the rest of the line to the program untouched, so no quoting of the hook's holds there.
    if (/^--%(?:\s|$)/.test(s.slice(this.at))) {
      while (this.at < s.length && s[this.at] !== "\n" && s[this.at] !== "|") this.at += 1;
      return this.made(start, { value: "--%", stopParsing: true });
    }
    while (this.at < s.length) {
      const c = s[this.at];
      if (" \t\r\n;|&)}{<>".includes(c)) break;
      if (c === "`") {
        if (s[this.at + 1] === "\n" || s[this.at + 1] === "\r") break;
        word.value += s[this.at + 1] ?? "";
        this.at += 2;
      } else if (c === "'") {
        this.literal(word);
      } else if (c === '"') {
        this.at += 1;
        this.expandable(word, false);
      } else if (c === "$") {
        this.variable(word);
      } else if (c === "(" || (c === "@" && this.at === start && "({".includes(s[this.at + 1]))) {
        if (c === "(" && this.at > start) break;
        const opening = c === "@" ? s[this.at + 1] : "(";
        this.at += c === "@" ? 2 : 1;
        word.inner.push(...this.list(opening === "(" ? ")" : "}"));
        word.dynamic = true;
      } else {
        word.value += c;
        this.at += 1;
      }
    }
    return this.made(start, word);
  }

  literal(word) {
    const s = this.source;
    let text = "";
    this.at += 1;
    while (this.at < s.length) {
      if (s[this.at] === "'" && s[this.at + 1] === "'") {
        text += "'";
        this.at += 2;
      } else if (s[this.at] === "'") {
        this.at += 1;
        break;
      } else {
        text += s[this.at];
        this.at += 1;
      }
    }
    word.value += text;
    this.strings.push(text);
  }

  literalHereString(word) {
    const s = this.source;
    const close = s.startsWith("'@", this.at) ? this.at - 1 : s.indexOf("\n'@", this.at);
    const stop = close < 0 ? s.length : close;
    const text = s.slice(this.at, Math.max(stop, this.at)).replace(/\r$/, "");
    this.at = close < 0 ? s.length : close + 3;
    word.value += text;
    this.strings.push(text);
  }

  expandable(word, hereString) {
    const s = this.source;
    const opened = this.at;
    let text = "";
    while (this.at < s.length) {
      const c = s[this.at];
      if (hereString && (this.at === opened || s[this.at - 1] === "\n") && s.startsWith('"@', this.at)) {
        this.at += 2;
        text = text.replace(/\r?\n$/, "");
        break;
      }
      if (!hereString && c === '"' && s[this.at + 1] === '"') {
        text += '"';
        this.at += 2;
      } else if (!hereString && c === '"') {
        this.at += 1;
        break;
      } else if (c === "`") {
        text += s[this.at + 1] ?? "";
        this.at += 2;
      } else if (c === "$") {
        this.variable(word);
      } else {
        text += c;
        this.at += 1;
      }
    }
    word.value += text;
    this.strings.push(text);
  }

  variable(word) {
    const s = this.source;
    if (s[this.at + 1] === "(") {
      this.at += 2;
      word.inner.push(...this.list(")"));
      word.dynamic = true;
    } else if (s[this.at + 1] === "{") {
      const stop = s.indexOf("}", this.at);
      this.at = stop < 0 ? s.length : stop + 1;
      word.dynamic = true;
    } else {
      const name = /^\$(?:[A-Za-z_]\w*(?::\w+)?|[?^$])/.exec(s.slice(this.at));
      if (name) {
        this.at += name[0].length;
        word.dynamic = true;
      } else {
        word.value += "$";
        this.at += 1;
      }
    }
  }
}
