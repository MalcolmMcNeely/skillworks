// PROTOTYPE — throwaway. Variant D, the verdict: C's table is the way in, and B's instrument is the session itself.
// The table replaces B's rail, so the bar at the top carries the way back and a jump to another session in the
// same repository.

import { SessionPane } from '../scrub/ScrubVariant';
import { format, repositoryLabel, sessionName } from '../sessionMeasures';
import { StoryIndex } from '../story/StoryIndex';
import type { SessionView } from '../useSessionView';
import './DuoVariant.css';

export function DuoVariant({ view }: { view: SessionView }) {
  const { session, sessions, go } = view;

  if (session === null) {
    return (
      <div className="story duo-index">
        <StoryIndex view={view} />
      </div>
    );
  }

  const siblings = sessions.filter((each) => each.repository === session.repository);

  return (
    <div className="scrub duo">
      <header className="duo-bar">
        <button type="button" className="duo-back" onClick={() => go({ session: null, step: null, prompt: null, activation: null })}>
          ← All sessions
        </button>
        <span className="duo-crumb">
          {repositoryLabel(session.repository)} <b>·</b> {session.person} <b>·</b> {format.day(session.startMs)} {format.clock(session.startMs)}
        </span>
        <label className="duo-jump">
          <span className="duo-jump-word">Jump to</span>
          <select value={session.id} onChange={(event) => go({ session: event.target.value, step: null, prompt: null, activation: null })}>
            {siblings.map((each) => (
              <option key={each.id} value={each.id}>
                {format.day(each.startMs)} {format.clock(each.startMs)} · {each.person} · {sessionName(each).slice(0, 48)}
              </option>
            ))}
          </select>
        </label>
      </header>
      <SessionPane key={session.id} view={view} session={session} />
    </div>
  );
}
