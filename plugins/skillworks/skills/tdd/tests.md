# Good and Bad Tests

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of internal parts.

```typescript
// GOOD: Tests observable behavior
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});
```

Characteristics:

- Deterministic
- Before it acts while the code runs, it waits on a fact the test sees
- Tests behavior users/callers care about
- Uses public API only
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test

Where appropriate, tests edge cases concerning concurrency, we often work on cloud based system which has at least 2 replicas active.

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```typescript
// BAD: Tests implementation details
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});
```

Red flags:

- Undeterministic
- Acts while the code runs, and trusts that the code got there first
- Mocking internal collaborators
- Testing private methods
- Asserting on call counts/order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Verifying through external means instead of interface

```typescript
// BAD: Bypasses interface to verify
test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});

// GOOD: Verifies through interface
test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

**Tautological tests**: Expected value restates the implementation, so the test passes by construction.

```typescript
// BAD: Expected value is recomputed the way the code computes it
test("calculateTotal sums line items", () => {
  const items = [{ price: 10 }, { price: 5 }];
  const expected = items.reduce((sum, i) => sum + i.price, 0);
  expect(calculateTotal(items)).toBe(expected);
});

// GOOD: Expected value is an independent, known literal
test("calculateTotal sums line items", () => {
  expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
});
```

**Racing tests**: Act while the code runs, and trust that the code got there first. They pass on a quiet machine, and hang or fail on a busy one.

An act is anything a test does to the code while it runs: a cancel, a close of a request, a clock move, a second request, a stop of a host. Ask of every act: "What fact does this act wait on?"

A fact is something the test sees at the point the act needs, such as a stand-in saying that it holds a call. A sleep is not a fact. The code's own order is not a fact either, because the code can change its order for a good reason. When nothing the test sees answers the question, add the fact to the stand-in.

The team's determinism rule, `docs/agents/rules/determinism.md`, holds the full rule under Order of events.

```typescript
// BAD: Cancels, and trusts that the read already reached the store
test("cancelling a read releases the store", async () => {
  const store = holdingStore();
  const controller = new AbortController();
  readOrders(store, controller.signal);
  controller.abort();
  await store.released;
});

// GOOD: Waits until the store holds the read, then cancels
test("cancelling a read releases the store", async () => {
  const store = holdingStore();
  const controller = new AbortController();
  readOrders(store, controller.signal);
  await store.holding;
  controller.abort();
  await store.released;
});
```
