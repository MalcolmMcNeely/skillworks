import { describe, expect, it } from 'vitest';
import { ariaSort, describeList, sortMark } from './skills';

describe('describeList', () => {
  it('joins the values it was given', () => {
    expect(describeList(['alpha', 'beta'])).toBe('alpha, beta');
  });

  it('shows a dash when a skill has never fired anywhere', () => {
    expect(describeList([])).toBe('—');
  });
});

describe('sortMark', () => {
  it('points up when the column sorts ascending', () => {
    expect(sortMark('asc')).toBe(' ▲');
  });

  it('points down when the column sorts descending', () => {
    expect(sortMark('desc')).toBe(' ▼');
  });

  it('marks nothing when the column is not sorted', () => {
    expect(sortMark(false)).toBe('');
  });
});

describe('ariaSort', () => {
  it('names the direction a sorted column runs in', () => {
    expect(ariaSort('asc')).toBe('ascending');
    expect(ariaSort('desc')).toBe('descending');
  });

  it('says none when the column is not sorted', () => {
    expect(ariaSort(false)).toBe('none');
  });
});
