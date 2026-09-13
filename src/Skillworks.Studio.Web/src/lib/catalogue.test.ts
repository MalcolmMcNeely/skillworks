import { describe, expect, it } from 'vitest';
import { describeCatalogueLocation } from './catalogue';

describe('describeCatalogueLocation', () => {
  it('names the path when the catalogue is there', () => {
    expect(describeCatalogueLocation({ path: '/repo/plugins', exists: true })).toBe(
      'Catalogue found at /repo/plugins',
    );
  });

  it('names the path it looked in when the catalogue is missing', () => {
    expect(describeCatalogueLocation({ path: '/repo/plugins', exists: false })).toBe(
      'No catalogue at /repo/plugins',
    );
  });
});
