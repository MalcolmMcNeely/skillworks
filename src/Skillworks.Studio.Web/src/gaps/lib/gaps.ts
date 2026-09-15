// Most gaps arrive as nothing at all, so only this word tells a screen which it is.
export type GapKind =
  | 'complete'
  | 'unreachable'
  | 'telemetryOff'
  | 'telemetryUnknown'
  | 'quiet';

export interface Gap {
  kind: GapKind;
  missing: string | null;
}

export interface Signal {
  word: string;
  tone: 'live' | 'quiet' | 'warned' | 'failed';
}

// The word only says which Gap, as the Gap's own sentence opens from it.
const signals: Record<GapKind, Signal> = {
  complete: { word: 'Live', tone: 'live' },
  unreachable: { word: 'No signal', tone: 'failed' },
  telemetryOff: { word: 'Telemetry off', tone: 'warned' },
  telemetryUnknown: { word: 'Telemetry unknown', tone: 'warned' },
  quiet: { word: 'Quiet', tone: 'quiet' },
};

export function signalOf(kind: GapKind): Signal {
  return signals[kind];
}
