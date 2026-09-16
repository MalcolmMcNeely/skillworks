import { getJson, putJson } from '../../http/api/json';

export interface TeamSettings {
  path: string;
  text: string;
}

export interface TelemetryState {
  emitting: boolean;
  settingsPath: string;
  readable: boolean;
  collectorEndpoint: string;
  restartNote: string;
  problem: string | null;
  team: TeamSettings;
}

export function fetchTelemetry(signal?: AbortSignal): Promise<TelemetryState> {
  return getJson<TelemetryState>('/api/telemetry/switch', signal);
}

export function setTelemetry(emitting: boolean): Promise<TelemetryState> {
  return putJson<TelemetryState>('/api/telemetry/switch', { emitting });
}
