import { useMemo } from 'react';
import { namedIn, noFindingsWord, type FindingsPage, type Named } from '../../lib/verdict/findings';
import { momentOf } from '../../lib/verdict/moment';
import { describeClock, titleOf, type Mark } from '../../lib/steps';
import type { Spell } from '../../lib/timeline/view';
import { MomentDrawing } from './MomentDrawing';

function Card({
  named,
  marks,
  whole,
  onShow,
}: {
  named: Named;
  marks: readonly Mark[];
  whole: Spell;
  onShow: (named: Named) => void;
}) {
  const moment = useMemo(() => momentOf(named, marks, whole), [named, marks, whole]);

  return (
    <li className={`finding-card${named.known ? '' : ' is-unknown'}`}>
      <header className="finding-head">
        <h3 className="finding-word">{named.word}</h3>
        <span className="finding-subject">{named.finding.subject ?? ''}</span>
      </header>
      <p className="finding-figures">
        <span className="finding-figure">{named.reading}</span>
        <span className="micro">bar {named.barReading}</span>
      </p>
      <p className="micro finding-note">{named.note}</p>

      {/* Nothing to draw or move to: only a span could have measured this bar and the run has none. */}
      {named.known ? (
        <>
          <MomentDrawing moment={moment} from={named.startMs} to={named.endMs} />
          {moment.faults.length === 0 ? (
            <p className="micro finding-note">No fault in this moment.</p>
          ) : (
            <ol className="finding-faults" aria-label="Faults in this moment">
              {moment.faults.map((mark) => (
                <li key={mark.step.id} className="finding-fault">
                  <span className="finding-fault-clock">{describeClock(mark.startMs, true)}</span>
                  <span className="finding-fault-title">{titleOf(mark.step)}</span>
                  <span className="finding-fault-words">{mark.step.words ?? ''}</span>
                </li>
              ))}
            </ol>
          )}
          <button type="button" className="finding-show" onClick={() => onShow(named)}>
            Show in the Timeline
          </button>
        </>
      ) : (
        <p className="micro finding-note">Only a span can say, and this run has none.</p>
      )}
    </li>
  );
}

export function Findings({
  findings,
  marks,
  whole,
  onShow,
}: {
  findings: FindingsPage | null;
  marks: readonly Mark[];
  whole: Spell;
  onShow: (named: Named) => void;
}) {
  const named = namedIn(findings);

  return (
    <section className="session-panel session-findings" aria-label="Findings">
      <header className="panel-head">
        <h2>Findings</h2>
      </header>

      {named.length === 0 ? (
        <p className="session-word">{noFindingsWord(findings)}</p>
      ) : (
        <ul className="finding-cards">
          {named.map((each) => (
            <Card key={each.kind} named={each} marks={marks} whole={whole} onShow={onShow} />
          ))}
        </ul>
      )}
    </section>
  );
}
