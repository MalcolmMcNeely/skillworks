import { getJson, postJson } from '../../http/api/json';

export interface IngestStatus {
  running: boolean;
  completedPasses: number;
  transcriptsSeen: number;
  transcriptsTotal: number;
  transcriptsRead: number;
  activationsAdded: number;
  lastPassWasFull: boolean;
  lastRefreshUtc: string | null;
  faults: number;
}

export interface TranscriptFault {
  path: string;
  // Zero means the whole file would not open.
  line: number;
  reason: string;
  noticedUtc: string;
}

export function fetchIngest(signal?: AbortSignal): Promise<IngestStatus> {
  return getJson<IngestStatus>('/api/ingest', signal);
}

export function fetchFaults(signal?: AbortSignal): Promise<TranscriptFault[]> {
  return getJson<TranscriptFault[]>('/api/ingest/faults', signal);
}

// The pass runs in the background, so what comes back is not its result.
export function refreshIngest(): Promise<IngestStatus> {
  return postJson<IngestStatus>('/api/ingest');
}

export function fullIngest(): Promise<IngestStatus> {
  return postJson<IngestStatus>('/api/ingest/full');
}
