// PROTOTYPE — throwaway. Where the reader is lives in the address bar, so flipping variants keeps the same session,
// prompt and step on screen and each variant is judged on the same data.

import { useMemo } from 'react';
import { useSearchParams } from 'react-router';
import { fortnight } from './sessionFixture';
import type { Session } from './sessionModel';
import { noRepository } from './sessionMeasures';

export interface ViewPlace {
  // null: no repository chosen yet. '' is the group of sessions with no repository.
  repository: string | null;
  by: 'recent' | 'person';
  person: string | null;
  session: string | null;
  prompt: number | null;
  step: string | null;
  activation: number | null;
}

let fixture: { now: number; sessions: Session[] } | null = null;

// Drawn once per page load, so a re-render never moves the fortnight under the reader.
function readFixture() {
  if (fixture === null) {
    const now = Date.now();
    fixture = { now, sessions: fortnight(now) };
  }
  return fixture;
}

const readNumber = (value: string | null) => (value === null || value === '' || Number.isNaN(Number(value)) ? null : Number(value));

export function useSessionView() {
  const [params, setParams] = useSearchParams();
  const { now, sessions } = readFixture();

  const repo = params.get('repo');
  const place: ViewPlace = {
    repository: repo === null ? null : repo === noRepository ? '' : repo,
    by: params.get('by') === 'person' ? 'person' : 'recent',
    person: params.get('person'),
    session: params.get('session'),
    prompt: readNumber(params.get('prompt')),
    step: params.get('step'),
    activation: readNumber(params.get('activation')),
  };

  const session = useMemo(() => sessions.find((each) => each.id === place.session) ?? null, [sessions, place.session]);

  // Moving to a new session pushes, so the back button walks out the way the reader came in. Everything finer replaces.
  const go = (patch: Partial<ViewPlace>) => {
    const next = new URLSearchParams(params);
    const write = (key: string, value: string | number | null | undefined) => {
      if (value === undefined) return;
      if (value === null) next.delete(key);
      else next.set(key, String(value));
    };

    write('repo', patch.repository === undefined ? undefined : patch.repository === null ? null : patch.repository === '' ? noRepository : patch.repository);
    write('by', patch.by);
    write('person', patch.person);
    write('session', patch.session);
    write('prompt', patch.prompt);
    write('step', patch.step);
    write('activation', patch.activation);

    const coarse = patch.repository !== undefined || patch.person !== undefined || patch.session !== undefined || patch.by !== undefined;
    setParams(next, { replace: !coarse });
  };

  return { now, sessions, place, session, go };
}

export type SessionView = ReturnType<typeof useSessionView>;
