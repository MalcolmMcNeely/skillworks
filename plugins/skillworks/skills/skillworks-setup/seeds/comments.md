# Comments

The YAML block at the end holds the doc comment setting. The rules for ordinary comments are the text
alone.

## Ordinary comments

A comment records why: a hidden constraint, a workaround, or a choice a reader would otherwise undo.
The names in the code say what it does, so a comment never says it again.

A comment makes sense to a reader who has never seen the ticket or the ADR. It states the reason
itself and carries no issue, ticket or ADR number.

A test body may mark its parts with `// Arrange`, `// Act` and `// Assert`.

## What a sweep keeps and cuts

A comment sweep judges each comment against this table. A comment not in the table is judged by the
rules above.

| Comment | Verdict |
|---|---|
| `// increment the counter` | Cut: restates the line below it |
| `// constructor` | Cut: the syntax already says so |
| `// loop through the users` | Cut |
| `// retry 3 times`, above `retries: 3` | Cut: the value says so |
| `// returns null on a cache miss, not undefined` | Cut: says what the code does, not why |
| `// 3 retries: the vendor rate-limits bursts above 4` | Keep: the reason lives nowhere in the code |
| `// must run before the auth middleware or the session is empty` | Keep: a hidden ordering constraint |

A sweep leaves linter and compiler directives (`eslint-disable`, `@ts-expect-error`, `#pragma`) and
licence headers alone. They are instructions to tools and legal text, not comments for a reader.

## Doc comments

In C#, a doc comment is a `///` line or a `/** */` block.

In TypeScript, a doc comment is a `/**` that begins a line: the first characters after any whitespace
are `/**`, and not `/**/`. It runs to the next `*/`. A `/**` later on a line never starts one, so a
`/**` in a string or after `//` is not a doc comment.

A TypeScript block that holds only tags is not a doc comment. A block holds only tags when every line
between its `/**` and its `*/` that is not empty, with any leading `*` removed, starts with `@`. Text
after a tag belongs to that tag, so `/** @type {Config} */` and `/** @deprecated Use b instead. */`
hold only tags.

In Python, a doc comment is a docstring: a `"""` or a `'''` that opens a module, a class or a
function. It opens one when nothing but space sits before it on its line, and the nearest line above
it that is neither empty nor a `#` comment ends with `:`, or there is no such line. A triple quote
anywhere else opens a value, so `QUERY = """`, and the mark that closes it, are both free.

`doc-comments` decides where they go:

- `false`: no file has doc comments. The names of types and members document the code.
- `true`: code files may carry doc comments, and test files keep to ordinary comments.

```yaml
doc-comments: false
```
