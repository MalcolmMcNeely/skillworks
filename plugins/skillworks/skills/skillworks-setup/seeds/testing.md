# Testing

This rule holds the team's taste in tests. The method is the same in every repo: red before green,
one vertical slice at a time, and tests at seams through public interfaces. What a good test looks
like here is the team's to change, and this rule is where it changes.

The YAML block at the end is empty, because the rule has no settings.

## Seams

Tests are integration style. A test drives the code through a real interface, and never through
mocks of its internal parts.

- Test at the highest seam that works, and at the fewest seams. A test at a high seam survives a
  refactor beneath it.
- Prefer a seam the code already has to one made for the test.
- A test checks what a caller sees through the interface, and never reaches past it, such as by
  querying the database the code just wrote to.

## What to mock

Mock at a system boundary only:

- An external API, such as a payment or an email service.
- A database, sometimes. Prefer a test database, or the real one in a container.
- Time and randomness.
- The file system, sometimes.

Never mock:

- The team's own classes and modules.
- An internal collaborator.
- Anything else the team controls.

Code that calls an external service gives each operation a function of its own, such as
`getUser` and `getOrders`, and not one generic `fetch` that takes the endpoint. A mock of one
operation then returns one shape and holds no conditional logic, and a test shows which
operations it uses.

Where an interface needs faking, the team names its fake library here, so the next agent does not
pick a different one. Until it does, a test uses the library the repo's tests already use.

## Fakes

A fake is used where the real thing cannot be made to misbehave, or where it forces a race, and not
otherwise. A real dependency in a container proves the queries and the parsing, and that is the code
most likely to be wrong.

A stand-in is a fake the test writes by hand. It is right where the real thing cannot be made to
fail: a dependency that is down, that fails, or that never answers, which a running container cannot
be made to be. It is right too where the test needs a fact the real thing does not show, as Order of
events in the determinism rule says.

## One test

- A test holds one logical assertion.
- A test's name says what the test proves, and not how: "a user can check out with a valid cart",
  and not "checkout calls the payment service".
- A test that asserts on how many times a call was made, or on the order of calls, is a red flag. It
  checks how the code works, so it breaks on a refactor that changes no behaviour.

## What judges this rule

No check reads this rule, so a green suite does not prove it. A setting is
enforced only once a check exists that reads it, and this rule has none. The `standards` review
judges each change by it.

```yaml
```
