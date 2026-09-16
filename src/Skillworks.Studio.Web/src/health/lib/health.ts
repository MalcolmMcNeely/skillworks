import type { SymbolTable } from '../../alphabets/lib/alphabets';

export type PartState = 'working' | 'starting' | 'off' | 'broken';

export interface Part {
  name: string;
  state: PartState;
  detail: string;
  action: string | null;
}

export interface Lamp {
  callSign: string;
  state: PartState;
  glyph: string;
  word: string;
  opens: Pick<Part, 'detail' | 'action'> | null;
}

const lampMarks: Record<PartState, { glyph: string; word: string }> = {
  working: { glyph: '●', word: 'Working' },
  starting: { glyph: '◌', word: 'Starting' },
  off: { glyph: '○', word: 'Off' },
  broken: { glyph: '✕', word: 'Broken' },
};

export const lampSymbols: SymbolTable = {
  alphabet: 'condition',
  glyphs: Object.values(lampMarks).map((mark) => mark.glyph),
};

const callSigns: Record<string, string> = {
  'Events store': 'Store',
};

// The telemetry switch shows this part's state, so a lamp for it would say the same thing twice.
const shownBySwitch = 'Claude Code telemetry';

function lamp(callSign: string, state: PartState, opens: Lamp['opens']): Lamp {
  return { callSign, state, ...lampMarks[state], opens };
}

export function lampsOf(report: { parts: readonly Part[] } | null, failure: string | null): Lamp[] {
  // Ahead of the report: parts read before the API stopped answering may no longer hold.
  if (failure !== null) {
    return [lamp('API', 'broken', { detail: failure, action: 'Start Studio with aspire run.' })];
  }

  if (report === null) {
    return [lamp('API', 'starting', null)];
  }

  return report.parts
    .filter((part) => part.name !== shownBySwitch)
    .map((part) =>
      lamp(
        callSigns[part.name] ?? part.name,
        part.state,
        part.state === 'broken' || part.state === 'off' ? { detail: part.detail, action: part.action } : null,
      ),
    );
}
