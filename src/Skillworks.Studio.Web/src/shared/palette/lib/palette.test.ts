import { describe, expect, it } from 'vitest';
import { contrast } from './contrast';
import { palette, paletteProperties, surfaces } from './palette';

describe('palette', () => {
  for (const [name, surface] of Object.entries(surfaces)) {
    for (const text of surface.text) {
      it(`keeps ${text} text at 4.5:1 or more on the ${name} ground`, () => {
        expect(contrast(palette[text], palette[surface.ground])).toBeGreaterThanOrEqual(4.5);
      });
    }

    for (const mark of surface.marks) {
      it(`keeps ${mark} marks at 3:1 or more on the ${name} ground`, () => {
        expect(contrast(palette[mark], palette[surface.ground])).toBeGreaterThanOrEqual(3);
      });
    }
  }
});

describe('paletteProperties', () => {
  it('hands every colour to the stylesheet as a custom property named for it', () => {
    expect(paletteProperties).toMatchObject({ '--void': palette.void, '--ink-soft': palette.inkSoft });
    expect(Object.keys(paletteProperties)).toHaveLength(Object.keys(palette).length);
  });
});
