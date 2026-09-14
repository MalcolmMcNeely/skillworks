import { describe, expect, it } from 'vitest';
import { byActivations, readSort, withSort } from './sorting';

describe('readSort', () => {
  it('ranks by activations, most first, when the address bar says nothing', () => {
    expect(readSort(new URLSearchParams())).toEqual(byActivations);
  });

  it('reads the column and the direction the address bar names', () => {
    expect(readSort(new URLSearchParams('sort=cost&desc=no'))).toEqual({ column: 'cost', desc: false });
    expect(readSort(new URLSearchParams('sort=cost'))).toEqual({ column: 'cost', desc: true });
  });
});

describe('withSort', () => {
  it('leaves the address bar alone while the sort is the one it started with', () => {
    expect(withSort(new URLSearchParams('skill=tdd'), byActivations).toString()).toBe('skill=tdd');
  });

  it('writes the sort beside the filter, so one address describes the whole view', () => {
    const written = withSort(new URLSearchParams('skill=tdd'), { column: 'cost', desc: false });

    expect(written.get('skill')).toBe('tdd');
    expect(written.get('sort')).toBe('cost');
    expect(written.get('desc')).toBe('no');
  });

  it('comes back to the same sort it wrote out', () => {
    const sort = { column: 'name', desc: false };

    expect(readSort(withSort(new URLSearchParams(), sort))).toEqual(sort);
  });
});
