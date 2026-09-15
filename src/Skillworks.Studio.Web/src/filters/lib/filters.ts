export interface Filter {
  // A date as a date input writes one, 2026-09-01. Both ends are taken in whole.
  from: string;
  to: string;
  repository: string;
  skill: string;
}

export const everything: Filter = { from: '', to: '', repository: '', skill: '' };

// Both ends in, so a span of one day has from equal to to.
export interface Span {
  from: string;
  to: string;
  lookback: boolean;
}

export const dayMilliseconds = 24 * 60 * 60 * 1000;

export function readFilter(params: URLSearchParams): Filter {
  return {
    from: params.get('from') ?? '',
    to: params.get('to') ?? '',
    repository: params.get('repository') ?? '',
    skill: params.get('skill') ?? '',
  };
}

// The address bar and the API take the same parameters, so the address shows what was asked.
export function filterParams(filter: Filter): URLSearchParams {
  const params = new URLSearchParams();

  for (const [name, value] of Object.entries(filter)) {
    if (value !== '') {
      params.set(name, value);
    }
  }

  return params;
}

export function filterQuery(filter: Filter): string {
  const query = filterParams(filter).toString();

  return query === '' ? '' : `?${query}`;
}

export function isEverything(filter: Filter): boolean {
  return filterParams(filter).size === 0;
}

export function describeFilter(filter: Filter): string {
  const parts: string[] = [];

  if (filter.from !== '' && filter.to !== '') {
    parts.push(`${filter.from} to ${filter.to}`);
  } else if (filter.from !== '') {
    parts.push(`from ${filter.from}`);
  } else if (filter.to !== '') {
    parts.push(`up to ${filter.to}`);
  }

  if (filter.repository !== '') {
    parts.push(`in ${filter.repository}`);
  }

  if (filter.skill !== '') {
    parts.push(filter.skill);
  }

  return parts.join(', ');
}

export function describeSpan(span: Span): string {
  if (span.lookback) {
    // Read as UTC midnights, so a daylight saving change cannot make a day 23 hours long.
    const days = (Date.parse(`${span.to}T00:00:00Z`) - Date.parse(`${span.from}T00:00:00Z`)) / dayMilliseconds + 1;

    return days === 1 ? 'today' : `the last ${days} days`;
  }

  return span.from === span.to ? span.from : `${span.from} to ${span.to}`;
}

// Spelled out, not left to the locale, which writes September as Sept in some places and Sep in others.
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function describeDay(day: string): string {
  const [, month, date] = day.split('-');

  return `${date} ${months[Number(month) - 1] ?? month}`;
}

export function describeEmpty(filter: Filter): string {
  return isEverything(filter)
    ? 'No skill has fired yet.'
    : `Nothing matched ${describeFilter(filter)}.`;
}

// The address bar can name a choice the list lacks, and a select would silently show another.
export function withChosen(choices: readonly string[], chosen: string): string[] {
  return chosen === '' || choices.includes(chosen) ? [...choices] : [chosen, ...choices];
}
