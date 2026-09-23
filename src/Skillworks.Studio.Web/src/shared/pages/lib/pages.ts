import type { SymbolTable } from '../../alphabets/lib/alphabets';

export interface Page {
  address: string;
  name: string;
  glyph: string;
  tabTitle: string;
  parent: Page | null;
  built: boolean;
}

// Home alone sits at the top, so a page below it always has one to go up to.
export type PageBelowHome = Page & { parent: Page };

const studioMark = 'Skillworks';

// No such page has no address of its own, so it is in no list and builds its own name and title.
export const noSuchPageName = 'No such page';

export function tabTitleOf(name: string): string {
  return `${name} · ${studioMark}`;
}

// The parent's own type is carried through, so only Home ends up with nothing above it.
function page<Above extends Page | null>(
  address: string,
  name: string,
  glyph: string,
  parent: Above,
  built: boolean,
): Page & { parent: Above } {
  return {
    address,
    name,
    glyph,
    // Home is Studio itself, so its tab carries the mark alone.
    tabTitle: parent === null ? studioMark : tabTitleOf(name),
    parent,
    built,
  };
}

export const pageGlyphs = {
  home: '⌂',
  dashboard: '▦',
  sessions: '▤',
  author: '✎',
  test: '✓',
  publish: '↑',
} as const;

export const pageSymbols: SymbolTable = { alphabet: 'identity', glyphs: Object.values(pageGlyphs) };

export const home = page('/', 'Home', pageGlyphs.home, null, true);

export const dashboard: PageBelowHome = page('/dashboard', 'Dashboard', pageGlyphs.dashboard, home, true);

export const sessions: PageBelowHome = page('/sessions', 'Sessions', pageGlyphs.sessions, home, true);

// Home shows a panel for every job, so a job still to come is listed before it is built.
export const pages: readonly Page[] = [
  home,
  dashboard,
  sessions,
  page('/author', 'Author', pageGlyphs.author, home, false),
  page('/test', 'Test', pageGlyphs.test, home, false),
  page('/publish', 'Publish', pageGlyphs.publish, home, false),
];

export function pagesBelow(parent: Page): readonly Page[] {
  return pages.filter((below) => below.parent === parent);
}
