// Most gaps arrive as nothing at all, so only this word tells a screen which it is.
export type GapKind =
  | 'complete'
  | 'unreachable'
  | 'truncated'
  | 'telemetryOff'
  | 'telemetryUnknown'
  | 'quiet';

export interface Gap {
  kind: GapKind;
  missing: string | null;
}

// Not telemetry off: it speaks for this machine only, so the store may still hold events a filter left out.
export function explainsEmpty(kind: GapKind): boolean {
  return kind === 'unreachable' || kind === 'quiet' || kind === 'telemetryUnknown';
}
