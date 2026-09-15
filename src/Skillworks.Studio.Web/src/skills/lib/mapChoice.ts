import type { MapOrder, MapView } from './map';

export interface MapChoice {
  view: MapView;
  order: MapOrder;
}

export const costMostFirst: MapChoice = { view: 'cost', order: 'most' };

// Anything else reads as the default, so a hand-typed address still opens a map.
export function readMapChoice(params: URLSearchParams): MapChoice {
  return {
    view: params.get('view') === 'activations' ? 'activations' : costMostFirst.view,
    order: params.get('order') === 'least' ? 'least' : costMostFirst.order,
  };
}

// The defaults are left out, so an untouched map has a clean address to share.
export function withMapChoice(params: URLSearchParams, choice: MapChoice): URLSearchParams {
  const written = new URLSearchParams(params);

  if (choice.view === costMostFirst.view) {
    written.delete('view');
  } else {
    written.set('view', choice.view);
  }

  if (choice.order === costMostFirst.order) {
    written.delete('order');
  } else {
    written.set('order', choice.order);
  }

  return written;
}
