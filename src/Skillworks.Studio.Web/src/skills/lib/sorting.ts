// One column, because ranking by several is a query language and finding the extremes needs none.
export interface Sort {
  column: string;
  desc: boolean;
}

export const byActivations: Sort = { column: 'activations', desc: true };

export function readSort(params: URLSearchParams): Sort {
  const column = params.get('sort');

  if (column === null || column === '') {
    return byActivations;
  }

  // Anything but a plain "no" ranks downward, so a hand-typed address still means something.
  return { column, desc: params.get('desc') !== 'no' };
}

// The starting sort is left out, so an untouched table has a clean address to share.
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
