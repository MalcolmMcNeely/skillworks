export interface Filter {
  // A date as a date input writes one, 2026-09-01. Both ends are taken in whole.
  from: string;
  to: string;
  repository: string;
  skill: string;
  // Empty asks for both depths, so no run is ever hidden from a reader who did not ask for that.
  depth: string;
}

export const everything: Filter = { from: '', to: '', repository: '', skill: '', depth: '' };

// Both ends in, so a span of one day has from equal to to.
export interface Span {
  from: string;
  to: string;
}

export function readFilter(params: URLSearchParams): Filter {
  return {
    from: params.get('from') ?? '',
    to: params.get('to') ?? '',
    repository: params.get('repository') ?? '',
    skill: params.get('skill') ?? '',
    depth: params.get('depth') ?? '',
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

// Spelled out, not left to the locale, which writes September as Sept in some places and Sep in others.
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function describeDay(day: string): string {
  const [, month, date] = day.split('-');

  return `${date} ${months[Number(month) - 1] ?? month}`;
}

// The address bar can name a choice the list lacks, and a select would silently show another.
export function withChosen(choices: readonly string[], chosen: string): string[] {
  return chosen === '' || choices.includes(chosen) ? [...choices] : [chosen, ...choices];
}
