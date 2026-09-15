export type SortDirection = false | 'asc' | 'desc';

export interface TokenSplit {
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheCreationTokens: number;
}

export interface SkillSpend extends TokenSplit {
  // US dollars, as Claude Code estimated them.
  cost: number;
}

// Words, not a zero or a dash: a plugin outside Anthropic's marketplaces has its Turns sent unnamed, so what it spent is not known.
const notNamed = 'Not named';

// Not the reader's locale: costs are in US dollars, so figures group and point the way dollars do.
const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  // Four places, or a firing that costs a fraction of a cent would round to free.
  maximumFractionDigits: 4,
});

const tokens = new Intl.NumberFormat('en-US');

export function describeList(values: readonly string[] | null): string {
  if (values === null) {
    return notNamed;
  }

  return values.length === 0 ? '—' : values.join(', ');
}

export function describeMoney(amount: number | null): string {
  return amount === null ? notNamed : money.format(amount);
}

function describeTokens(count: number): string {
  return tokens.format(count);
}

export function describeSplit(spend: TokenSplit | null): string {
  if (spend === null) {
    return notNamed;
  }

  return [
    `in ${describeTokens(spend.inputTokens)}`,
    `out ${describeTokens(spend.outputTokens)}`,
    `cache read ${describeTokens(spend.cacheReadTokens)}`,
    `cache creation ${describeTokens(spend.cacheCreationTokens)}`,
  ].join(' · ');
}

export function describeUnnamedSpend(spend: SkillSpend): string {
  return (
    `Unnamed spend: ${describeMoney(spend.cost)} · ${describeSplit(spend)}. ` +
    'Claude Code does not name a skill from a plugin outside Anthropic’s marketplaces, so this spend is in no skill’s cost.'
  );
}

export function sortMark(sorted: SortDirection): string {
  if (sorted === 'asc') {
    return ' ▲';
  }

  return sorted === 'desc' ? ' ▼' : '';
}

export function ariaSort(sorted: SortDirection): 'ascending' | 'descending' | 'none' {
  if (sorted === 'asc') {
    return 'ascending';
  }

  return sorted === 'desc' ? 'descending' : 'none';
}
