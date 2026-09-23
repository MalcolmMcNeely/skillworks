import { describe, expect, it } from 'vitest';
import { dashboard, home, noSuchPageName, pageGlyphs, pageSymbols, pages, pagesBelow, sessions, tabTitleOf } from './pages';

describe('pages', () => {
  it('lists every page of Studio in the order Home shows them', () => {
    expect(pages.map((page) => page.name)).toEqual(['Home', 'Dashboard', 'Sessions', 'Author', 'Test', 'Publish']);
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
    expect(pages.filter((page) => page !== home).map((page) => page.parent)).toEqual(Array(5).fill(home));
  });

  it('marks Home, the Dashboard and Sessions built and the jobs still to come not built', () => {
    expect(pages.filter((page) => page.built)).toEqual([home, dashboard, sessions]);
  });

  it('opens Studio at the plain address', () => {
    expect(home.address).toBe('/');
  });

  it('gives the Dashboard an address of its own', () => {
    expect(dashboard.address).toBe('/dashboard');
  });

  it('puts the Dashboard below Home', () => {
    expect(dashboard.parent).toBe(home);
  });

  it('gives Sessions an address of its own', () => {
    expect(sessions.address).toBe('/sessions');
  });

  it('titles the tab Skillworks on Home, so the tab never changes name on load', () => {
    expect(home.tabTitle).toBe('Skillworks');
  });

  it('titles the tab with the page name on every page below Home', () => {
    expect(dashboard.tabTitle).toBe('Dashboard · Skillworks');
  });
});

describe('pageGlyphs', () => {
  it('gives each page the symbol a reader sees on Home', () => {
    expect(pageGlyphs).toEqual({ home: '⌂', dashboard: '▦', sessions: '▤', author: '✎', test: '✓', publish: '↑' });
  });

  it('is the one place the pages take their symbols from', () => {
    expect(pages.map((page) => page.glyph)).toEqual([
      pageGlyphs.home,
      pageGlyphs.dashboard,
      pageGlyphs.sessions,
      pageGlyphs.author,
      pageGlyphs.test,
      pageGlyphs.publish,
    ]);
  });

  it('names a page and nothing else, so no page reads as a state or a cause', () => {
    expect(pageSymbols.alphabet).toBe('identity');
  });
});

describe('tabTitleOf', () => {
  it('titles the screen an address that goes nowhere lands on, which no page list names', () => {
    expect(tabTitleOf(noSuchPageName)).toBe('No such page · Skillworks');
  });
});

describe('pagesBelow', () => {
  it('names the jobs Home shows, in the order the list holds them', () => {
    expect(pagesBelow(home).map((page) => page.name)).toEqual(['Dashboard', 'Sessions', 'Author', 'Test', 'Publish']);
  });

  it('leaves out the page asked about, so Home never leads back to Home', () => {
    expect(pagesBelow(home)).not.toContain(home);
  });

  it('gives a page with nothing under it an empty list', () => {
    expect(pagesBelow(dashboard)).toEqual([]);
  });
});
