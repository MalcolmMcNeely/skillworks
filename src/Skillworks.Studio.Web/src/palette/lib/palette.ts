// The stylesheet and the contrast test both read these, so no colour reaches the screen untested.
export const palette = {
  void: '#04070c',
  panel: '#07111a',
  rule: '#19333b',
  line: '#3a7682',
  hud: '#6fe3f5',
  pressed: '#18333d',
  ink: '#d3ecf4',
  inkSoft: '#8fb2c0',
  inkFaint: '#6a8d9b',
  tileCool: '#080f14',
  tileHot: '#1f3f47',
  live: '#4fe08a',
  failed: '#ff6259',
  warned: '#ffd166',
  unnamed: '#b58cff',
  unnamedHatch: '#2a2140',
} as const;

export type PaletteColour = keyof typeof palette;

export interface Surface {
  ground: PaletteColour;
  text: readonly PaletteColour[];
  // Only marks that carry meaning, as a rule that only divides need not clear 3:1.
  marks: readonly PaletteColour[];
}

export const surfaces: Record<string, Surface> = {
  page: {
    ground: 'void',
    text: ['ink', 'inkSoft', 'inkFaint', 'hud', 'live', 'failed', 'warned', 'unnamed'],
    marks: ['hud', 'line', 'live', 'failed', 'warned', 'unnamed'],
  },
  rail: {
    ground: 'panel',
    text: ['ink', 'inkSoft', 'inkFaint', 'hud', 'live', 'failed', 'warned', 'unnamed'],
    marks: ['hud', 'line', 'live', 'failed', 'warned', 'unnamed'],
  },
  pressedKey: {
    ground: 'pressed',
    text: ['ink', 'inkSoft', 'hud'],
    marks: ['hud'],
  },
  // A tile's ground runs from cool to hot with its Each, so both ends are held to the thresholds.
  coolTile: {
    ground: 'tileCool',
    text: ['ink', 'inkSoft', 'hud'],
    // The edge only on a cool tile: a hot tile stands out from the page by its own brightness.
    marks: ['hud', 'inkFaint', 'line'],
  },
  hotTile: {
    ground: 'tileHot',
    text: ['ink', 'inkSoft', 'hud'],
    marks: ['hud', 'inkFaint'],
  },
  unnamedTile: {
    ground: 'unnamedHatch',
    text: ['unnamed', 'inkSoft'],
    marks: [],
  },
};

export const paletteProperties: Record<string, string> = Object.fromEntries(
  Object.entries(palette).map(([name, hex]) => [`--${name.replace(/[A-Z]/g, (capital) => `-${capital.toLowerCase()}`)}`, hex]),
);
