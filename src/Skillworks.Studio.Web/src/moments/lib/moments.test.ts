import { describe, expect, it } from 'vitest';
import { describeMoment } from './moments';

describe('describeMoment', () => {
  it('reads the moment in UTC, whatever clock the reader is sitting at', () => {
    expect(describeMoment('2026-09-02T14:48:23.182+00:00')).toBe('2026-09-02 14:48:23 UTC');
  });

  it('reads an offset moment at the hour it actually happened', () => {
    expect(describeMoment('2026-09-02T16:48:23.182+02:00')).toBe('2026-09-02 14:48:23 UTC');
  });

  it('shows a moment it cannot read as it was recorded', () => {
    expect(describeMoment('not a moment')).toBe('not a moment');
  });
});
