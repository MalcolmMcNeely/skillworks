import { describeCount, describeLength, describeMoney } from '../../../figures/lib/figures';
import { briefNote, noReport, noSubagentsWord, tallyOf, type AgentSpell } from '../../lib/panels/agents';
import { inRange, type Range } from '../../lib/view';
import { notKnown } from '../../lib/sessions';
import { describeClock } from '../../lib/steps';

function Said({ what, words, missing }: { what: string; words: string | null; missing: string | null }) {
  return (
    <div className="agent-said">
      <p className="agent-mark">{what}</p>
      {words === null ? null : <p className="agent-words">{words}</p>}
      {missing === null ? null : <p className="agent-missing">{missing}</p>}
    </div>
  );
}

function Opened({ spell, onClose }: { spell: AgentSpell; onClose: () => void }) {
  const { agent } = spell;

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
        {describeClock(spell.startMs, true)} · {describeLength(agent.lengthMs)} ·{' '}
        {describeCount(agent.toolCalls)} tool calls · {describeMoney(agent.cost)} ·{' '}
        {describeCount(agent.faults)} faults
      </p>
      <Said what="Brief" words={agent.brief} missing={briefNote(agent)} />
      <Said what="Report" words={agent.report} missing={agent.report === null ? noReport : null} />
    </div>
  );
}

function Row({ spell, open, onOpen }: { spell: AgentSpell; open: boolean; onOpen: (spell: AgentSpell) => void }) {
  const { agent } = spell;

  return (
    <li>
      <button type="button" className={`agent-row${open ? ' is-open' : ''}`} onClick={() => onOpen(spell)}>
        <span className="call-name">{agent.name}</span>
        <span className="agent-kind">{agent.type ?? notKnown}</span>
        <span className="agent-figure">{describeLength(agent.lengthMs)}</span>
        <span className="agent-figure">{describeCount(agent.toolCalls)} tool calls</span>
        <span className="agent-figure">{describeMoney(agent.cost)}</span>
        <span className="agent-figure">{describeCount(agent.faults)} faults</span>
      </button>
    </li>
  );
}

// Every row and every figure here reads the View alone, or the panel would answer a question nobody asked.
export function SubagentPanel({
  agentSpells,
  traced,
  view,
  opened,
  onOpen,
  onClose,
}: {
  agentSpells: readonly AgentSpell[];
  traced: boolean;
  view: Range | null;
  opened: string | null;
  onOpen: (spell: AgentSpell) => void;
  onClose: () => void;
}) {
  const shown = inRange(agentSpells, view);
  const tally = tallyOf(shown);
  const open = opened === null ? null : (agentSpells.find((spell) => spell.agent.id === opened) ?? null);

  return (
    <section className="session-panel" aria-label="Subagents">
      <header className="panel-head">
        <h2>Subagents</h2>
        <p className="micro panel-figure">
          {describeCount(tally.subagents)} subagents · {describeCount(tally.toolCalls)} tool calls ·{' '}
          {describeMoney(tally.cost)} · {describeCount(tally.faults)} faults
          {view === null ? '' : ' in view'}
        </p>
      </header>

      {open === null ? null : <Opened spell={open} onClose={onClose} />}

      {shown.length === 0 ? (
        <p className="session-word">{noSubagentsWord(traced, agentSpells.length)}</p>
      ) : (
        <ol className="call-list">
          {shown.map((spell) => (
            <Row key={spell.agent.id} spell={spell} open={spell.agent.id === opened} onOpen={onOpen} />
          ))}
        </ol>
      )}
    </section>
  );
}
