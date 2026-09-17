// Not the reader's locale: costs are in US dollars, so figures group and point the way dollars do.
const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  // Four places, or a firing that costs a fraction of a cent would round to free.
  maximumFractionDigits: 4,
});

const counts = new Intl.NumberFormat('en-US');

const tokenCounts = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

export function describeMoney(amount: number): string {
  return money.format(amount);
}

export function describeCount(count: number): string {
  return counts.format(count);
}

export function describeTokens(count: number): string {
  return tokenCounts.format(count);
}

export function describeShare(share: number): string {
  return `${Math.round(share * 100)}%`;
}
