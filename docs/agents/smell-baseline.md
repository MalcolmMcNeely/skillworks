# Smell baseline

The Standards axis's fixed set: Fowler's code smells (_Refactoring_, ch.3), with four test smells beneath them. It applies even when a repo documents nothing, and it is overridden wherever the repo does.

Two rules bind it:

- **The repo overrides.** A documented repo standard always wins. Where the repo endorses what the baseline would flag, the smell is suppressed.
- **Always a judgement call.** Each item is a labelled heuristic ("possible Feature Envy"), never a hard breach.

Skip anything tooling already enforces. Each item reads *what it is* → *how to fix*; match it against the diff:

## The twelve

- **Mysterious Name** — a function, variable or type whose name does not say what it does or holds. → Rename it. If no honest name comes, the design is murky.
- **Duplicated Code** — the same logic shape appears in more than one hunk or file in the change. → Extract the shared shape, call it from both.
- **Feature Envy** — a method that reaches into another object's data more than its own. → Move the method onto the data it envies.
- **Data Clumps** — the same few fields or parameters keep travelling together (a type wanting to be born). → Bundle them into one type, pass that.
- **Primitive Obsession** — a primitive or string standing in for a domain concept that deserves its own type. → Give the concept its own small type.
- **Repeated Switches** — the same `switch` or `if`-cascade on the same type recurs across the change. → Replace with polymorphism, or one map both sites share.
- **Shotgun Surgery** — one logical change forces scattered edits across many files in the diff. → Gather what changes together into one module.
- **Divergent Change** — one file or module is edited for several unrelated reasons. → Split it so each module changes for one reason.
- **Speculative Generality** — abstraction, parameters or hooks added for needs the spec or the ticket does not have. → Delete it. Inline back until a real need shows.
- **Message Chains** — long `a.b().c().d()` navigation the caller should not depend on. → Hide the walk behind one method on the first object.
- **Middle Man** — a class or function that mostly just delegates onward. → Cut it, call the real target direct.
- **Refused Bequest** — a subclass or implementer that ignores or overrides most of what it inherits. → Drop the inheritance, use composition.

## The four

The items above judge code. A test carries them and four of its own, under one question: **what change to the code would make this test fail?** A test with no answer is a finding however tidy it reads, because a suite that cannot go red buys nothing and is read as proof.

- **Tautological Assertion** — the expected side is worked out the way the code works it out, so both sides move together and no defect can show. → Write the expected value out by hand.
- **Untriggered Fixture** — the input holds nothing the behaviour under test acts on, so the assertion would still hold with that behaviour deleted. → Put the trigger in the fixture, and settle it by deleting the behaviour and watching the test go red.
- **Unguarded Enumeration** — a test walks files, rows or elements and judges what it found without proving it found any, so an empty walk passes. → Pin the count the walk is expected to reach.
- **Stub Echo** — a stub is handed a value and the assertion only checks that value came back, so it measures the stub. → Assert on what the code made of the value, not on the value.
