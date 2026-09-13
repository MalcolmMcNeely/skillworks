import { describe, expect, it } from 'vitest';
import { describeList } from './skills';

describe('describeList', () => {
  it('joins the values it was given', () => {
    expect(describeList(['alpha', 'beta'])).toBe('alpha, beta');
  });

  it('shows a dash when a skill has never fired anywhere', () => {
    expect(describeList([])).toBe('—');
  });
});
