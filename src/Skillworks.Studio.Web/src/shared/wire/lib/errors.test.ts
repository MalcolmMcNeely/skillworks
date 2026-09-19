import { describe, expect, it } from 'vitest';
import { describeFetchFailure } from './errors';

describe('describeFetchFailure', () => {
  it('shows what an Error had to say', () => {
    expect(describeFetchFailure(new Error('GET /api/skills returned 500'))).toBe(
      'GET /api/skills returned 500',
    );
  });

  it('names the likely cause when the thrown value carries no message', () => {
    expect(describeFetchFailure('boom')).toBe('Could not reach the API');
  });
});
