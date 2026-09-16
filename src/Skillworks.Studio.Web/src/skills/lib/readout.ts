import type { SymbolTable } from '../../alphabets/lib/alphabets';
import { triggerMarks } from '../../provenance/lib/triggers';
import type { PlacedTile, Size } from './map';
import { describeCount, describeMoney, describeTokens, notNamed, type SkillSummary } from './skills';
import { tokensIn } from './totals';

// A readout follows the pointer until it is pinned, and only the mark says which of the two it is.
export const readoutGlyphs = { pinned: '◆' } as const;

export const readoutSymbols: SymbolTable = { alphabet: 'condition', glyphs: Object.values(readoutGlyphs) };

export interface ReadoutRow {
  label: string;
  value: string;
  // Words for a value written in glyphs, as a screen reader reads ✦ as nothing or as its Unicode name.
  reading: string | null;
}

// A word, not a dash, which a screen reader reads as a pause or not at all.
const nothing = 'None';

const hourMs = 60 * 60 * 1000;

// The last firing is known only to the hour, so this never claims a minute it does not have.
export function describeAgo(instant: string, now: number): string {
  const hours = Math.floor((now - Date.parse(instant)) / hourMs);

  if (hours < 1) {
    return 'This hour';
  }

  return hours < 48 ? `${hours}h` : `${Math.floor(hours / 24)}d`;
}

function listed(names: readonly string[] | null): string {
  if (names === null) {
    return notNamed;
  }

  return names.length === 0 ? nothing : names.join(', ');
}

function inWords(label: string, value: string): ReadoutRow {
  return { label, value, reading: null };
}

export function readoutRows(skill: SkillSummary, now: number): ReadoutRow[] {
  const marks = triggerMarks(skill.triggers);

  return [
    inWords('Cost', describeMoney(skill.spend?.cost ?? null)),
    inWords('Activations', describeCount(skill.activations)),
    // A Cost with nothing to share it across is not a Cost that went unnamed.
    inWords('Each', skill.activations === 0 ? nothing : describeMoney(skill.each)),
    inWords('Tokens', skill.spend === null ? notNamed : describeTokens(tokensIn(skill.spend))),
    inWords('Model', listed(skill.models)),
    inWords('Effort', listed(skill.efforts)),
    inWords('Last', skill.lastFired === null ? nothing : describeAgo(skill.lastFired, now)),
    {
      label: 'Via',
      value: marks.map((mark) => `${mark.glyph}${describeCount(mark.activations)}`).join(' ') || nothing,
      reading: marks.map((mark) => `${mark.word} ${describeCount(mark.activations)}`).join('. ') || null,
    },
    inWords('Repositories', listed(skill.repositories)),
  ];
}

// Fixed, so the readout does not resize as the pointer moves from one tile to the next.
export const readoutSize = { width: 236, height: 236 };

const gap = 8;

function clamped(at: number, most: number): number {
  return Math.max(0, Math.min(most, at));
}

// Never over its own tile, and never off the map, so no figure is hidden or cut off.
export function readoutAt(placed: PlacedTile, map: Size): { left: number; top: number } {
  const right = placed.x + placed.width + gap;
  const left = placed.x - readoutSize.width - gap;
  const beside =
    right + readoutSize.width <= map.width ? right : left >= 0 ? left : placed.x + placed.width / 2 - readoutSize.width / 2;

  return {
    left: clamped(beside, map.width - readoutSize.width),
    top: clamped(placed.y, map.height - readoutSize.height),
  };
}
