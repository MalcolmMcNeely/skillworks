/**
 * The one way every view narrows: a span of days, a repository and a skill. An empty string means
 * that part is not narrowed, so one shape covers "last week in this project" and "all time
 * everywhere" without a null in sight.
 */
export interface Filter {
  /** A date, as an `input type="date"` writes one: `2026-09-01`. Both ends are taken in whole. */
  from: string;
  to: string;
  repository: string;
  skill: string;
}

/** All time, everywhere, every skill. What the page shows before anything is chosen. */
export const everything: Filter = { from: '', to: '', repository: '', skill: '' };

/**
 * The filter the address bar is describing. Reading it from there rather than from state is what
 * makes it survive a reload, a bookmark and the back button, with nothing to save and restore.
 */
export function readFilter(params: URLSearchParams): Filter {
  return {
    from: params.get('from') ?? '',
    to: params.get('to') ?? '',
    repository: params.get('repository') ?? '',
    skill: params.get('skill') ?? '',
  };
}

/**
 * The filter as parameters. The address bar and the API take the same ones, so what a reader can
 * see in the address bar is exactly what was asked of the API.
 */
export function filterParams(filter: Filter): URLSearchParams {
  const params = new URLSearchParams();

  for (const [name, value] of Object.entries(filter)) {
    if (value !== '') {
      params.set(name, value);
    }
  }

  return params;
}

/** The same again as a query string, ready to hang off an API path. Empty when nothing is narrowed. */
export function filterQuery(filter: Filter): string {
  const query = filterParams(filter).toString();

  return query === '' ? '' : `?${query}`;
}

export function isEverything(filter: Filter): boolean {
  return filterParams(filter).size === 0;
}

/** The filter in words, so a message about it names what was actually asked. */
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

/**
 * What an empty table means. A filter that matches nothing is an answer, not a failure, so it is
 * said as one and it names the filter that emptied it.
 *
 * @param whyEmpty
 * The API's reason the source behind the table has nothing in it, when there is one. It comes
 * first, because a missing source explains an empty table better than a filter does: with nothing
 * to read from, every filter matches nothing and blaming this one would send a reader to widen a
 * date range that was never the problem.
 */
export function describeEmpty(filter: Filter, whyEmpty: string | null = null): string {
  if (whyEmpty !== null) {
    return whyEmpty;
  }

  return isEverything(filter)
    ? 'No skill has fired yet.'
    : `Nothing matched ${describeFilter(filter)}.`;
}

/**
 * The choices a filter offers, with whatever is already chosen kept among them. A filter read out
 * of the address bar can name a repository the list has not got, and a chooser that silently showed
 * something else would be telling the reader the wrong thing about what they are looking at.
 */
export function withChosen(choices: readonly string[], chosen: string): string[] {
  return chosen === '' || choices.includes(chosen) ? [...choices] : [chosen, ...choices];
}
