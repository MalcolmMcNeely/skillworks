---
name: tdd
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
---

# Test-Driven Development

TDD is the red → green loop. This skill holds the method that makes that loop produce tests worth keeping: where tests go, the anti-patterns, and the rules of the loop. The method is the same in every repo. Every section applies on every cycle — consult them before and during the loop, not after.

Before the first test, read `docs/agents/domain.md`: it says where this repo keeps its glossary and its ADRs. Read the glossary that claims the code you touch, where there is one, so test names and interface vocabulary match the project's domain language, and respect ADRs in the area you're touching.

## The testing rule

`docs/agents/rules/testing.md` at the repo root is the team's taste in tests: what to mock and what not to, how a test is named, how much one test asserts, and how high and how few the seams are. Read it before the first test, and write every test by it. Where it and this skill seem to disagree, the rule is the team's word on taste, and this skill is the method.

If `docs/agents/rules/testing.md` or `docs/agents/domain.md` is missing, stop. Tell the user which file is missing, that `/skillworks:skillworks-setup` writes it, and that no test was written. Under the spec loop this is work you cannot do, so begin your report with a line that starts with `BLOCKED` and holds that message: the driver reads that line and stops the spec loop at once.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A test that doesn't care about internal structure survives refactors.

Read [tests.md](tests.md) before the first test when the work has a mock, a stand-in or a test that acts while the code runs. It holds a bad and a good example of the implementation-coupled, tautological and racing anti-patterns.

Read [swappable-boundaries.md](swappable-boundaries.md) when the testing rule says to mock something the work touches. It holds an example of code that lets a test swap that thing in, and of code that does not.

## Seams — where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**State the seams before the first test, then go on.** Write down the seams under test before writing any test. With a spec, the seams are the ones in its Testing Decisions. With no spec, pick them by the testing rule. Never wait for a yes: the user can stop you once the seams are stated. You can't test everything — naming the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

When the shape of that interface is itself in question — how deep the module is, where the seam belongs, what the interface should expose — call the Skill tool with "skillworks:codebase-design" for the vocabulary. It is the shared source of the module, interface, depth, seam, adapter, leverage and locality terms, and it is a reference to consult, not a session to run.

## Anti-patterns

- **Implementation-coupled** — mocks internal collaborators, tests private methods, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological** — the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth — a known-good literal, a worked example, the spec.
- **Racing** — the test acts while the code runs (a cancel, a close of a request, a clock move, a second request) and trusts that the code got there first, so it passes on a quiet machine and hangs or fails on a busy one. Before every act, wait on a fact the test sees, such as a stand-in saying that it holds the call. A sleep is not a fact, and neither is the code's own order. When nothing the test sees is such a fact, add one to the stand-in.
- **Horizontal slicing** — writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead — one test → one implementation → repeat, each test a **tracer bullet** that responds to what the last cycle taught you.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Done.** The loop is done when every behavior the task asks for has a test that you ran and saw fail, and that now passes. Where a test passes on its first run because the code had the behavior before you started, say in your report that you did not see that test fail. The two rules above cut extras only: build every behavior the task asks for, completely.
- **Refactoring is not part of the loop.** It belongs to the review, not the red → green implementation cycle.
