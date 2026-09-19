// Most gaps arrive as nothing at all, so only this word tells a screen which it is.
export type GapKind =
  | 'complete'
  | 'unreachable'
  | 'shortened'
  | 'telemetryOff'
  | 'telemetryUnknown'
  | 'wordsOff'
  | 'quiet';

export interface Gap {
  kind: GapKind;
  missing: string | null;
}

export interface GapEnd {
  kind: 'end';
  gap: Gap;
}

// A Gap counting Activations alone would call a period that only spent quiet, so an answer may end without one.
export interface PlainEnd {
  kind: 'end';
}

// The events store and the trace store fall short apart from each other, so each names its own shortfall.
export interface StoresEnd {
  kind: 'end';
  events: Gap;
  traces: Gap;
}

export interface Signal {
  word: string;
  tone: 'live' | 'quiet' | 'warned' | 'failed';
}

// The word only says which Gap, as the Gap's own sentence opens from it.
const signals: Record<GapKind, Signal> = {
  complete: { word: 'Live', tone: 'live' },
  unreachable: { word: 'No signal', tone: 'failed' },
  shortened: { word: 'Cut short', tone: 'warned' },
  telemetryOff: { word: 'Telemetry off', tone: 'warned' },
  telemetryUnknown: { word: 'Telemetry unknown', tone: 'warned' },
  wordsOff: { word: 'Words withheld', tone: 'warned' },
  quiet: { word: 'Quiet', tone: 'quiet' },
};

export function signalOf(kind: GapKind): Signal {
  return signals[kind];
}

export const missingWords = {
  // A word, not a dash, which a screen reader reads as a pause or not at all.
  none: 'None',
  // A plugin outside Anthropic's marketplaces has its Turns sent unnamed, so the cost is hidden, not absent.
  notNamed: 'Not named',
  // Never a zero, so an outage never reads as a quiet week.
  noAnswer: '—',
} as const;
