import { describe, expect, it } from 'vitest';
import { contrast } from './contrast';

describe('contrast', () => {
  it('gives black on white the widest ratio there is', () => {
    expect(contrast('#000000', '#ffffff')).toBeCloseTo(21, 6);
  });

  it('gives a colour on itself no contrast at all', () => {
    expect(contrast('#6fe3f5', '#6fe3f5')).toBeCloseTo(1, 6);
  });

  it('gives the same ratio whichever colour is on top', () => {
    expect(contrast('#04070c', '#d3ecf4')).toBeCloseTo(contrast('#d3ecf4', '#04070c'), 6);
  });

  it('puts the darkest grey that passes for text on white just over 4.5:1', () => {
    expect(contrast('#767676', '#ffffff')).toBeCloseTo(4.54, 2);
    expect(contrast('#777777', '#ffffff')).toBeLessThan(4.5);
  });
});
