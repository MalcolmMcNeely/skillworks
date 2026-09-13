import { getJson, postJson } from './json';

/** `GET /api/ingest`, already shaped by the API. */
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

/** One line or file the ingest could not read and stepped over. */
export interface TranscriptFault {
  path: string;
  /** Zero means the whole file would not open. */
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

/** Asks for a pass over whatever has changed. The pass itself happens in the background. */
export function refreshIngest(): Promise<IngestStatus> {
  return postJson<IngestStatus>('/api/ingest');
}

/** Throws away everything already read and reads it all again, for after a parse is fixed. */
export function fullIngest(): Promise<IngestStatus> {
  return postJson<IngestStatus>('/api/ingest/full');
}
