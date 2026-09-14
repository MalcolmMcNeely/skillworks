import { getJson, putJson } from '../../fetching/api/json';

export interface TelemetryChange {
  name: string;
  from: string | null;
  to: string;
}

export interface TelemetryState {
  emitting: boolean;
  settingsPath: string;
  readable: boolean;
  collectorEndpoint: string;
  changes: TelemetryChange[];
  restartNote: string;
  problem: string | null;
}

export function fetchTelemetry(signal?: AbortSignal): Promise<TelemetryState> {
  return getJson<TelemetryState>('/api/telemetry/switch', signal);
}

export function setTelemetry(emitting: boolean): Promise<TelemetryState> {
  return putJson<TelemetryState>('/api/telemetry/switch', { emitting });
}
