# Swappable Boundaries

The testing rule says what to mock. Whatever it names, the code has to let a test swap it in.

## Use dependency injection

At a boundary, pass the dependency in rather than creating it inside:

```typescript
// Easy to swap
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard to swap
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```
