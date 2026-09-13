import { getJson, putJson } from './json';

/** One variable the switch would write, and the value it would displace. */
export interface TelemetryChange {
  name: string;
  from: string | null;
  to: string;
}

/** `GET /api/telemetry/switch`, already shaped by the API. */
export interface TelemetryState {
  emitting: boolean;
  settingsPath: string;
  readable: boolean;
  collectorEndpoint: string;
  changes: TelemetryChange[];
  restartNote: string;
  problem: string | null;
}

export function fetchTelemetry(signal: AbortSignal): Promise<TelemetryState> {
  return getJson<TelemetryState>('/api/telemetry/switch', signal);
}

/** Writes the settings, or throws with Studio's reason for refusing to. */
export function setTelemetry(emitting: boolean): Promise<TelemetryState> {
  return putJson<TelemetryState>('/api/telemetry/switch', { emitting });
}
