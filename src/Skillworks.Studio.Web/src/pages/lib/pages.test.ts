import { describe, expect, it } from 'vitest';
import { home, pages, watch } from './pages';

describe('pages', () => {
  it('lists every page of Studio in the order Home shows them', () => {
    expect(pages.map((page) => page.name)).toEqual(['Home', 'Watch', 'Author', 'Test', 'Publish']);
  });

  it('gives every page an address, a name, a glyph and a tab title', () => {
    for (const page of pages) {
      expect(page.address).not.toBe('');
      expect(page.name).not.toBe('');
      expect(page.glyph).not.toBe('');
      expect(page.tabTitle).not.toBe('');
    }
  });

  it('gives no two pages the same address, so an address names one page', () => {
    expect(new Set(pages.map((page) => page.address)).size).toBe(pages.length);
  });

  it('puts nothing above Home and Home above every other page, so the up button always leads somewhere', () => {
    expect(home.parent).toBeNull();
    expect(pages.filter((page) => page !== home).map((page) => page.parent)).toEqual(Array(4).fill(home));
  });

  it('marks Home and Watch built and the jobs still to come not built', () => {
    expect(pages.filter((page) => page.built)).toEqual([home, watch]);
  });

  it('opens Studio at the plain address', () => {
    expect(home.address).toBe('/');
  });

  it('gives Watch an address of its own', () => {
    expect(watch.address).toBe('/watch');
  });

  it('titles the tab Skillworks on Home, so the tab never changes name on load', () => {
    expect(home.tabTitle).toBe('Skillworks');
  });

  it('titles the tab with the page name on every page below Home', () => {
    expect(watch.tabTitle).toBe('Watch · Skillworks');
  });
});
