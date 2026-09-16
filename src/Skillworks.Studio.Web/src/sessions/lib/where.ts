import { sessions as page } from '../../pages/lib/pages';

// The Session is in the address's path, its Repository and person come back with it, and the Filter owns them.
export interface Where {
  // Null where the reader has opened no Exchange, which the whole run is.
  exchange: number | null;
  step: string | null;
}

export function readWhere(params: URLSearchParams): Where {
  const exchange = Number(params.get('exchange'));

  return {
    // A hand-typed address can name an Exchange that is not a whole count, and none is better than the first.
    exchange: params.has('exchange') && Number.isInteger(exchange) && exchange >= 0 ? exchange : null,
    step: params.get('step'),
  };
}

export function withWhere(params: URLSearchParams, where: Where): URLSearchParams {
  const written = new URLSearchParams(params);

  write(written, 'exchange', where.exchange === null ? null : String(where.exchange));
  write(written, 'step', where.step);

  return written;
}

// The whole address of one run, so a table row and a link in a panel lead to the same place.
export function sessionAddress(id: string, where: Where, params: URLSearchParams): string {
  const query = withWhere(params, where).toString();

  return `${page.address}/${encodeURIComponent(id)}${query === '' ? '' : `?${query}`}`;
}

function write(params: URLSearchParams, name: string, value: string | null): void {
  if (value === null) {
    params.delete(name);
  } else {
    params.set(name, value);
  }
}
