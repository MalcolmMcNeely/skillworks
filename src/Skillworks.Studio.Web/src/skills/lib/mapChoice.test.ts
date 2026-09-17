import { describe, expect, it } from 'vitest';
import { readMapChoice, withMapChoice } from './mapChoice';

describe('withMapChoice', () => {
  it('writes the figure and order the reader chose into the address', () => {
    const written = withMapChoice(new URLSearchParams('from=2026-09-01'), { figure: 'activations', order: 'least' });

    expect(written.toString()).toBe('from=2026-09-01&figure=activations&order=least');
  });

  it('leaves Cost and Most out, so an untouched map has a clean address to share', () => {
    const written = withMapChoice(new URLSearchParams('repository=skillworks&figure=activations&order=least'), {
      figure: 'cost',
      order: 'most',
    });

    expect(written.toString()).toBe('repository=skillworks');
  });
});

describe('readMapChoice', () => {
  it('reads back what it wrote, so a reload lands on the same map', () => {
    const choice = { figure: 'activations', order: 'least' } as const;

    expect(readMapChoice(withMapChoice(new URLSearchParams(), choice))).toEqual(choice);
  });

  it('reads Cost and Most from an address that names neither', () => {
    expect(readMapChoice(new URLSearchParams('from=2026-09-01'))).toEqual({ figure: 'cost', order: 'most' });
  });

  it('reads Cost and Most from an address that names a figure or order the map does not have', () => {
    expect(readMapChoice(new URLSearchParams('figure=tokens&order=newest'))).toEqual({ figure: 'cost', order: 'most' });
  });
});
