/**
 * How a table is ranked. One column, because a table ranked by three at once is a query language
 * and the spec asks for the extremes to be findable without one.
 */
export interface Sort {
  column: string;
  desc: boolean;
}

/** What the skill table shows before a heading is clicked: the skills that fire most, first. */
export const byActivations: Sort = { column: 'activations', desc: true };

/**
 * The sort the address bar is describing. It lives there beside the filter so that opening an
 * activation and coming back lands on the table the reader built, not on a fresh one.
 */
export function readSort(params: URLSearchParams): Sort {
  const column = params.get('sort');

  if (column === null || column === '') {
    return byActivations;
  }

  // Anything but a plain "no" ranks downward, so a hand-typed address still means something.
  return { column, desc: params.get('desc') !== 'no' };
}

/**
 * The filter with the sort written beside it. The starting sort is left out rather than spelled
 * out, so a reader who has narrowed nothing and clicked nothing has a clean address to share.
 */
export function withSort(params: URLSearchParams, sort: Sort): URLSearchParams {
  const written = new URLSearchParams(params);

  if (sort.column === byActivations.column && sort.desc === byActivations.desc) {
    written.delete('sort');
    written.delete('desc');

    return written;
  }

  written.set('sort', sort.column);

  if (!sort.desc) {
    written.set('desc', 'no');
  } else {
    written.delete('desc');
  }

  return written;
}
