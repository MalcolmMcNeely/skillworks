# Writing ADRs

Every new ADR goes to the one folder that `adr-folder` names, in the YAML block at the end of `steering-file docs/agents/domain.md`, whatever context it is about. Create that folder lazily — only when the first ADR is needed.

## Shape

The team owns what an ADR looks like. Read `steering-file docs/agents/adr-format.md` for the template and the optional sections, and write each new ADR in that shape.

If `steering-file docs/agents/adr-format.md` ends with a non-zero status, the file is missing, so stop. Tell the user that the file is missing, that `/skillworks:skillworks-setup` writes it, and that no ADR was written.

## Numbering

A new ADR is named `<number>-<slug>.md`. Its number is one above the highest leading number of any `<number>-<slug>.md` file in the folder, padded to the digit count of the file with the highest number: after `041` comes `042`, and after `0007` comes `0008`. An empty or missing folder starts at `0001`.

## When to offer an ADR

All three of these must be true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will look at the code and wonder "why on earth did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If a decision is easy to reverse, skip it — you'll just reverse it. If it's not surprising, nobody will wonder why. If there was no real alternative, there's nothing to record beyond "we did the obvious thing."

### What qualifies

- **Architectural shape.** "We're using a monorepo." "The write model is event-sourced, the read model is projected into Postgres."
- **Integration patterns between contexts.** "Ordering and Billing communicate via domain events, not synchronous HTTP."
- **Technology choices that carry lock-in.** Database, message bus, auth provider, deployment target. Not every library — just the ones that would take a quarter to swap out.
- **Boundary and scope decisions.** "Customer data is owned by the Customer context; other contexts reference it by ID only." The explicit no-s are as valuable as the yes-s.
- **Deliberate deviations from the obvious path.** "We're using manual SQL instead of an ORM because X." Anything where a reasonable reader would assume the opposite. These stop the next engineer from "fixing" something that was deliberate.
- **Constraints not visible in the code.** "We can't use AWS because of compliance requirements." "Response times must be under 200ms because of the partner API contract."
- **Rejected alternatives when the rejection is non-obvious.** If you considered GraphQL and picked REST for subtle reasons, record it — otherwise someone will suggest GraphQL again in six months.
