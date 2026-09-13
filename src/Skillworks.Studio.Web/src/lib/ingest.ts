/**
 * How the ingest reads as sentences. Structural, so this module stays pure — it never imports the
 * wire types that happen to match it.
 */

/** How far the read has got: the answer to "is this table empty, or just not filled in yet". */
export function describeIngest(status: {
  running: boolean;
  completedPasses: number;
  transcriptsSeen: number;
  transcriptsTotal: number;
  lastPassWasFull: boolean;
}): string {
  if (status.running) {
    return status.transcriptsTotal === 0
      ? 'Looking for transcripts…'
      : `Reading transcript ${status.transcriptsSeen} of ${status.transcriptsTotal}.`;
  }

  if (status.completedPasses === 0) {
    return 'The first read has not started yet.';
  }

  if (status.transcriptsTotal === 0) {
    return 'There are no transcripts to read.';
  }

  // Named as a full read when that is what finished, so a developer who asked for one is told it
  // is the one that came back.
  return status.lastPassWasFull
    ? `Read all ${status.transcriptsTotal} transcripts again, from scratch.`
    : `Read all ${status.transcriptsTotal} transcripts.`;
}

/** When the numbers on screen last moved, so a stale table is never read as a fresh one. */
export function describeRefresh(lastRefreshUtc: string | null): string {
  return lastRefreshUtc === null
    ? 'Not refreshed yet.'
    : `Last refreshed ${new Date(lastRefreshUtc).toLocaleString()}.`;
}

/** How much of the transcripts was stepped over, as a sentence rather than a bare number. */
export function describeFaults(faults: number): string {
  if (faults === 0) {
    return 'Nothing was skipped.';
  }

  return faults === 1
    ? '1 piece of transcript was skipped.'
    : `${faults} pieces of transcript were skipped.`;
}

/**
 * Whether the list on screen is all of them. The API caps what it hands back, and a list that is
 * shorter than the count would otherwise read as a contradiction.
 */
export function describeFaultList(shown: number, total: number): string {
  return shown < total ? `Showing the first ${shown} of ${total}.` : `Showing all ${shown}.`;
}

/** One skipped piece, named the way a developer would have to open it. */
export function describeFault(fault: { path: string; line: number; reason: string }): string {
  const where = fault.line === 0 ? fault.path : `${fault.path} line ${fault.line}`;

  return `${where}: ${fault.reason}`;
}
