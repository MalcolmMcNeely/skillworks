export interface Filter {
  // A date as a date input writes one, 2026-09-01. Both ends are taken in whole.
  from: string;
  to: string;
  repository: string;
  skill: string;
}

export const everything: Filter = { from: '', to: '', repository: '', skill: '' };

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

// A missing source comes first, or a reader widens a date range that was never the problem.
export function describeEmpty(filter: Filter, whyEmpty: string | null = null): string {
  if (whyEmpty !== null) {
    return whyEmpty;
  }

  return isEverything(filter)
    ? 'No skill has fired yet.'
    : `Nothing matched ${describeFilter(filter)}.`;
}

// The address bar can name a choice the list lacks, and a select would silently show another.
export function withChosen(choices: readonly string[], chosen: string): string[] {
  return chosen === '' || choices.includes(chosen) ? [...choices] : [chosen, ...choices];
}
