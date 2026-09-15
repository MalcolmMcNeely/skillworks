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

  return status.lastPassWasFull
    ? `Read all ${status.transcriptsTotal} transcripts again, from scratch.`
    : `Read all ${status.transcriptsTotal} transcripts.`;
}

export function describeRefresh(lastRefreshUtc: string | null): string {
  return lastRefreshUtc === null
    ? 'Not refreshed yet.'
    : `Last refreshed ${new Date(lastRefreshUtc).toLocaleString()}.`;
}

export function describeFaults(faults: number): string {
  if (faults === 0) {
    return 'Nothing was skipped.';
  }

  return faults === 1
    ? '1 piece of transcript was skipped.'
    : `${faults} pieces of transcript were skipped.`;
}

// The API caps the list, which would otherwise seem to contradict the count.
export function describeFaultList(shown: number, total: number): string {
  return shown < total ? `Showing the first ${shown} of ${total}.` : `Showing all ${shown}.`;
}

export function describeFault(fault: { path: string; line: number; reason: string }): string {
  const where = fault.line === 0 ? fault.path : `${fault.path} line ${fault.line}`;

  return `${where}: ${fault.reason}`;
}
