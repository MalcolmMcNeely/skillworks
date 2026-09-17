import type { MapFigure, MapOrder } from './map';

export interface MapChoice {
  figure: MapFigure;
  order: MapOrder;
}

export const costMostFirst: MapChoice = { figure: 'cost', order: 'most' };

// Anything else reads as the default, so a hand-typed address still opens a map.
export function readMapChoice(params: URLSearchParams): MapChoice {
  return {
    figure: params.get('figure') === 'activations' ? 'activations' : costMostFirst.figure,
    order: params.get('order') === 'least' ? 'least' : costMostFirst.order,
  };
}

// The defaults are left out, so an untouched map has a clean address to share.
export function withMapChoice(params: URLSearchParams, choice: MapChoice): URLSearchParams {
  const written = new URLSearchParams(params);

  if (choice.figure === costMostFirst.figure) {
    written.delete('figure');
  } else {
    written.set('figure', choice.figure);
  }

  if (choice.order === costMostFirst.order) {
    written.delete('order');
  } else {
    written.set('order', choice.order);
  }

  return written;
}
