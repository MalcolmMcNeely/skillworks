import { describeCount, describeMoney } from '../../../figures/lib/figures';
import { briefNote, noReport, noSubagentsWord, tallyOf, type Depth, type Stint } from '../../lib/panels/agents';
import { inRange, type Range } from '../../lib/brush';
import { notKnown } from '../../lib/sessions';
import { describeClock, describeSpell } from '../../lib/steps';

function Said({ what, words, missing }: { what: string; words: string | null; missing: string | null }) {
  return (
    <div className="agent-said">
      <p className="agent-mark">{what}</p>
      {words === null ? null : <p className="agent-words">{words}</p>}
      {missing === null ? null : <p className="agent-missing">{missing}</p>}
    </div>
  );
}

function Opened({ stint, onClose }: { stint: Stint; onClose: () => void }) {
  const { agent } = stint;

  return (
    <div className="step-open">
      <p className="step-open-head">
        {agent.name}
        <span className="agent-kind">{agent.type ?? notKnown}</span>
        <button type="button" className="step-close" onClick={onClose}>
          Close
        </button>
      </p>
      <p className="micro">
        {describeClock(stint.startMs, true)} · {describeSpell(agent.lengthMs)} ·{' '}
        {describeCount(agent.toolCalls)} tool calls · {describeMoney(agent.cost)} ·{' '}
        {describeCount(agent.faults)} faults
      </p>
      <Said what="Brief" words={agent.brief} missing={briefNote(agent)} />
      <Said what="Report" words={agent.report} missing={agent.report === null ? noReport : null} />
    </div>
  );
}

function Row({ stint, open, onOpen }: { stint: Stint; open: boolean; onOpen: (stint: Stint) => void }) {
  const { agent } = stint;

  return (
    <li>
      <button type="button" className={`agent-row${open ? ' is-open' : ''}`} onClick={() => onOpen(stint)}>
        <span className="call-name">{agent.name}</span>
        <span className="agent-kind">{agent.type ?? notKnown}</span>
        <span className="agent-figure">{describeSpell(agent.lengthMs)}</span>
        <span className="agent-figure">{describeCount(agent.toolCalls)} tool calls</span>
        <span className="agent-figure">{describeMoney(agent.cost)}</span>
        <span className="agent-figure">{describeCount(agent.faults)} faults</span>
      </button>
    </li>
  );
}

// Every row and every figure here reads the brushed stretch alone, or the panel would answer a question nobody asked.
export function SubagentPanel({
  stints,
  depth,
  range,
  opened,
  onOpen,
  onClose,
}: {
  stints: readonly Stint[];
  depth: Depth;
  range: Range | null;
  opened: string | null;
  onOpen: (stint: Stint) => void;
  onClose: () => void;
}) {
  const shown = inRange(stints, range);
  const tally = tallyOf(shown);
  const open = opened === null ? null : (stints.find((stint) => stint.agent.id === opened) ?? null);

  return (
    <section className="session-panel" aria-label="Subagents">
      <header className="panel-head">
        <h2>Subagents</h2>
        <p className="micro panel-figure">
          {describeCount(tally.subagents)} subagents · {describeCount(tally.toolCalls)} tool calls ·{' '}
          {describeMoney(tally.cost)} · {describeCount(tally.faults)} faults
          {range === null ? '' : ' in the stretch in view'}
        </p>
      </header>

      {open === null ? null : <Opened stint={open} onClose={onClose} />}

      {shown.length === 0 ? (
        <p className="session-word">{noSubagentsWord(depth, stints.length)}</p>
      ) : (
        <ol className="call-list">
          {shown.map((stint) => (
            <Row key={stint.agent.id} stint={stint} open={stint.agent.id === opened} onOpen={onOpen} />
          ))}
        </ol>
      )}
    </section>
  );
}
