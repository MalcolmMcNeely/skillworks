import { daysLookedBack, type SessionsAnswer } from './sessions';

// In the browser and never sent to the stores: the Session id is not indexed, so a read by part of one scans every event.
export function narrowByLookup(answer: SessionsAnswer, text: string): SessionsAnswer {
  const start = text.trim().toLowerCase();

  return { ...answer, rows: answer.rows.filter((row) => row.session.id.toLowerCase().startsWith(start)) };
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

// Only a whole id, in lower case: a read by part of one scans every event, and the store matches exactly.
export function idToSend(answer: SessionsAnswer | null, text: string): string | null {
  const id = text.trim().toLowerCase();

  if (!uuid.test(id)) {
    return null;
  }

  const held = answer?.rows.some((row) => row.session.id.toLowerCase() === id) ?? false;

  return held ? null : id;
}

// Only an ended answer carries the start of the reach the days count back to.
export function describeNoRun(answer: SessionsAnswer): string | null {
  const days = daysLookedBack(answer);

  return answer.arriving || days === null ? null : `No run with that id in the last ${days} days.`;
}

// Counts the rows before they were narrowed, so the reader knows how far the list has read and not how many matched.
export function describeNoMatch(answer: SessionsAnswer, text: string): string | null {
  const start = text.trim();

  return start === ''
    ? null
    : `No run in the ${answer.rows.length} rows read so far starts with ${start}. Paste the whole id to look further back.`;
}
