export interface Page {
  address: string;
  name: string;
  glyph: string;
  tabTitle: string;
  parent: Page | null;
  built: boolean;
}

const studioMark = 'Skillworks';

// Home is Studio itself, so its tab carries the mark alone.
function page(address: string, name: string, glyph: string, parent: Page | null, built: boolean): Page {
  return {
    address,
    name,
    glyph,
    tabTitle: parent === null ? studioMark : `${name} · ${studioMark}`,
    parent,
    built,
  };
}

export const home = page('/', 'Home', '◈', null, true);

export const watch = page('/watch', 'Watch', '●', home, true);

// Home shows a panel for every job, so a job still to come is listed before it is built.
export const pages: readonly Page[] = [
  home,
  watch,
  page('/author', 'Author', '✦', home, false),
  page('/test', 'Test', '✓', home, false),
  page('/publish', 'Publish', '↑', home, false),
];
