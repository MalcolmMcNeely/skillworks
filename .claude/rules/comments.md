# Comments

The YAML block at the end holds the doc comment setting. The rules for ordinary comments are the text
alone.

## Ordinary comments

A comment records why: a hidden constraint, a workaround, or a choice a reader would otherwise undo.
The names in the code say what it does, so a comment never says it again.

A comment makes sense to a reader who has never seen the ticket or the ADR. It states the reason
itself and carries no issue, ticket or ADR number.

A test body may mark its parts with `// Arrange`, `// Act` and `// Assert`.

## Doc comments

In C#, a doc comment is a `///` line or a `/** */` block.

In TypeScript, a doc comment is a `/**` that begins a line: the first characters after any whitespace
are `/**`, and not `/**/`. It runs to the next `*/`. A `/**` later on a line never starts one, so a
`/**` in a string or after `//` is not a doc comment.

A TypeScript block that holds only tags is not a doc comment. A block holds only tags when every line
between its `/**` and its `*/` that is not empty, with any leading `*` removed, starts with `@`. Text
after a tag belongs to that tag, so `/** @type {Config} */` and `/** @deprecated Use b instead. */`
hold only tags.

`doc-comments` decides where they go:

- `false`: no file has doc comments. The names of types and members document the code.
- `true`: code files may carry doc comments, and test files keep to ordinary comments.

```yaml
doc-comments: false
```
