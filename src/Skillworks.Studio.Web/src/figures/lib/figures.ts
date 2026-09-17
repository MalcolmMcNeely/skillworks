// Not the reader's locale: costs are in US dollars, so figures group and point the way dollars do.
const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  // Four places, or an Activation that costs a fraction of a cent would round to free.
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

const second = 1_000;

const minute = 60 * second;

const hour = 60 * minute;

// A length can be four milliseconds or forty minutes, so the unit follows the figure.
export function describeLength(lengthMs: number): string {
  if (lengthMs < second) {
    return `${Math.round(lengthMs)} ms`;
  }

  if (lengthMs < minute) {
    return `${(lengthMs / second).toFixed(lengthMs < 10 * second ? 1 : 0)} s`;
  }

  if (lengthMs < hour) {
    return `${Math.floor(lengthMs / minute)}m ${twoFigures(Math.floor((lengthMs % minute) / second))}s`;
  }

  return `${Math.floor(lengthMs / hour)}h ${twoFigures(Math.floor((lengthMs % hour) / minute))}m`;
}

function twoFigures(value: number): string {
  return String(value).padStart(2, '0');
}
