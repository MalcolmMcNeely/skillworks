import type { SessionsAnswer } from './sessions';

// In the browser and never sent to the stores: the Session id is not indexed, so a read by part of one scans every event.
export function narrowByLookup(answer: SessionsAnswer, text: string): SessionsAnswer {
  const start = text.trim().toLowerCase();

  return { ...answer, rows: answer.rows.filter((row) => row.session.id.toLowerCase().startsWith(start)) };
}

// Counts the rows before they were narrowed, so the reader knows how far the list has read and not how many matched.
export function describeNoMatch(answer: SessionsAnswer, text: string): string | null {
  const start = text.trim();

  return start === ''
    ? null
    : `No run in the ${answer.rows.length} rows read so far starts with ${start}. Paste the whole id to look further back.`;
}
