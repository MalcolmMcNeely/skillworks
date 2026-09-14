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

A doc comment is a `///` line in C# or a `/**` block in TypeScript. A `/**` block that holds only `@`
tags, such as `/** @type {Config} */`, is not one.

`doc-comments` decides where they go:

- `false`: no file has doc comments. The names of types and members document the code.
- `true`: source files may have doc comments, and test files keep to ordinary comments.

```yaml
doc-comments: false
```
