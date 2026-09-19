import { describe, expect, it } from 'vitest';
import { depthKeyOf, narrowsByDepth } from './depthKeys';
import { everything } from './filters';

describe('depthKeyOf', () => {
  it('presses the key that asks for both when nothing is narrowed', () => {
    expect(depthKeyOf(everything)).toBe('');
  });

  it('presses the Depth the address bar asked for', () => {
    expect(depthKeyOf({ ...everything, depth: 'full' })).toBe('full');
    expect(depthKeyOf({ ...everything, depth: 'thin' })).toBe('thin');
  });

  it('presses nothing for a Depth nobody has', () => {
    expect(depthKeyOf({ ...everything, depth: 'deep' })).toBeNull();
  });
});

describe('narrowsByDepth', () => {
  it('counts a Depth the API reads as a narrowing', () => {
    expect(narrowsByDepth({ ...everything, depth: 'full' })).toBe(true);
    expect(narrowsByDepth({ ...everything, depth: 'thin' })).toBe(true);
  });

  it('counts nothing asked for as no narrowing', () => {
    expect(narrowsByDepth(everything)).toBe(false);
  });

  it('counts a Depth nobody has as no narrowing, as the API lists both depths for one', () => {
    expect(narrowsByDepth({ ...everything, depth: 'deep' })).toBe(false);
  });
});
