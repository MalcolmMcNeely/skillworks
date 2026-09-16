// PROTOTYPE — throwaway. Variant B, Scrub: one timeline instrument that every other part follows. A brush picks the
// stretch of the session in view, and a dock of tabs underneath reads that stretch, like a DAW or the browser devtools.

import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { SessionTip, useTip } from '../SessionTip';
import type { Session, SessionStep } from '../sessionModel';
import { activations, contextSeries, conversation, findings, format, repositoryLabel, sessionName, startOf, summarize, timeSplit, type Finding } from '../sessionMeasures';
import type { SessionView } from '../useSessionView';
import { ScrubContext } from './ScrubContext';
import { ScrubConversation } from './ScrubConversation';
import { ScrubInstrument } from './ScrubInstrument';
import { ScrubPicker, ScrubRail } from './ScrubRail';
import { clamp, useStable, windowAround, type Range, type ScrubTab } from './scrubRange';
import { ScrubSkills } from './ScrubSkills';
import { ScrubTime } from './ScrubTime';
import { ScrubTrace } from './ScrubTrace';
import './ScrubVariant.css';

const tabs: { key: ScrubTab; label: string }[] = [
  { key: 'trace', label: 'Trace' },
  { key: 'skills', label: 'Skill calls' },
  { key: 'conversation', label: 'Conversation' },
  { key: 'time', label: 'Where the time went' },
  { key: 'context', label: 'Context' },
];

const findingTab: Record<string, ScrubTab> = { hooks: 'time', waiting: 'time', cache: 'context', context: 'context' };

export function SessionPane({ view, session }: { view: SessionView; session: Session }) {
  const { place, go } = view;
  const tipState = useTip();
  const [range, setRange] = useState<Range | null>(null);
  const [cursor, setCursor] = useState<number | null>(null);
  const [tab, setTab] = useState<ScrubTab>(place.step !== null ? 'trace' : place.activation !== null ? 'skills' : 'time');
  const [dock, setDock] = useState(() => Math.round(window.innerHeight * 0.44));
  const main = useRef<HTMLDivElement>(null);

  const measured = useMemo(
    () => ({ activations: activations(session), exchanges: conversation(session), context: contextSeries(session), findings: findings(session) }),
    [session],
  );
  const inView = useMemo(() => ({ summary: summarize(session, range), split: timeSplit(session, range) }), [session, range]);

  const show = useStable(tipState.show);
  const hide = useStable(tipState.hide);
  const tip = useMemo(() => ({ show, hide }), [show, hide]);

  const selectStep = useStable((step: SessionStep) => {
    go({ step: step.id, prompt: step.prompt >= 0 ? step.prompt : null });
    setTab('trace');
  });
  const selectStepById = useStable((id: string) => {
    const step = session.steps.find((each) => each.id === id);
    if (step !== undefined) selectStep(step);
  });
  const chooseActivation = useStable((index: number) => {
    const activation = measured.activations[index];
    if (activation === undefined) return;
    go({ activation: index, prompt: activation.prompt.index });
    setRange(windowAround(activation.startMs, activation.endMs, session));
    setTab('skills');
  });
  const brush = useStable((next: Range | null) => setRange(next));
  const moveCursor = useStable((ms: number | null) => setCursor(ms));

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.shiftKey || event.altKey || event.ctrlKey || event.metaKey || event.defaultPrevented) return;
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      const target = event.target as HTMLElement | null;
      if (target?.closest('input, textarea, select, [contenteditable], [role="slider"]')) return;
      const count = measured.activations.length;
      if (count === 0) return;
      event.preventDefault();
      const forward = event.key === 'ArrowRight';
      const current = place.activation ?? (forward ? -1 : 0);
      chooseActivation((current + (forward ? 1 : -1) + count) % count);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [measured, place.activation, chooseActivation]);

  const followFinding = (finding: Finding) => {
    const first = session.steps.find((step) => step.id === finding.stepIds[0]);
    if (first !== undefined) {
      setRange(windowAround(startOf(first), first.at, session, 90_000));
      selectStep(first);
      return;
    }
    setRange(null);
    setTab(findingTab[finding.key] ?? 'time');
  };

  const resize = (event: ReactPointerEvent<HTMLDivElement>) => {
    const startY = event.clientY;
    const startHeight = dock;
    const room = main.current?.getBoundingClientRect().height ?? window.innerHeight;
    const target = event.currentTarget;
    target.setPointerCapture(event.pointerId);
    const move = (moved: PointerEvent) => setDock(clamp(startHeight - (moved.clientY - startY), 150, room - 260));
    const up = () => {
      target.removeEventListener('pointermove', move);
      target.removeEventListener('pointerup', up);
    };
    target.addEventListener('pointermove', move);
    target.addEventListener('pointerup', up);
  };

  const { summary } = inView;
  const whole = range === null;

  return (
    <div className="scrub-main" ref={main}>
      <header className="scrub-head">
        <div className="scrub-head-line">
          {session.running && (
            <span className="scrub-live">
              <i className="scrub-pulse" />
              Running
            </span>
          )}
          <h1 title={sessionName(session)}>{sessionName(session)}</h1>
          <span className="scrub-head-meta">
            {session.person} · {repositoryLabel(session.repository)} · {format.day(session.startMs)} {format.clock(session.startMs)} · {format.duration(session.endMs - session.startMs)} ·{' '}
            {session.entry === 'scripted' ? 'claude -p' : 'interactive'} · {session.version}
          </span>
          <dl className={`scrub-head-figures${whole ? '' : ' is-range'}`}>
            <div>
              <dt>{whole ? 'Cost' : 'Cost in view'}</dt>
              <dd className="is-hero">{format.usd(summary.costUsd)}</dd>
            </div>
            <div>
              <dt>Busy</dt>
              <dd>{format.duration(summary.busyMs)}</dd>
            </div>
            <div>
              <dt>Prompts</dt>
              <dd>{range === null ? session.prompts.length : session.prompts.filter((span) => span.endMs >= range[0] && span.startMs <= range[1]).length}</dd>
            </div>
            <div>
              <dt>Model</dt>
              <dd>
                {summary.mainCalls}
                <small>+{summary.otherCalls}</small>
              </dd>
            </div>
            <div>
              <dt>Tools</dt>
              <dd>{summary.toolCalls}</dd>
            </div>
            <div className={summary.failedTools + summary.apiErrors > 0 ? 'is-failed' : ''}>
              <dt>Faults</dt>
              <dd>{summary.failedTools + summary.apiErrors + summary.rejected}</dd>
            </div>
            <div>
              <dt>Peak context</dt>
              <dd>{format.tokens(summary.peakContext)}</dd>
            </div>
          </dl>
        </div>
        {measured.findings.length > 0 && (
          <ul className="scrub-flags" aria-label="Findings">
            {measured.findings.map((finding) => (
              <li key={finding.key}>
                <button type="button" className={`scrub-flag is-${finding.tone}`} onClick={() => followFinding(finding)} title={finding.detail}>
                  <i aria-hidden="true" />
                  {finding.title}
                </button>
              </li>
            ))}
          </ul>
        )}
      </header>

      <ScrubInstrument
        session={session}
        activations={measured.activations}
        range={range}
        cursor={cursor}
        selected={place.step}
        tip={tip}
        onRange={brush}
        onCursor={moveCursor}
        onSelect={selectStep}
        onActivation={chooseActivation}
      />

      <div className="scrub-grip" role="separator" aria-orientation="horizontal" aria-label="Resize the dock" onPointerDown={resize}>
        <i />
      </div>

      <section className="scrub-dock" style={{ height: dock }} aria-label="Dock">
        <div className="scrub-tabs" role="tablist">
          {tabs.map((each) => (
            <button key={each.key} type="button" role="tab" aria-selected={tab === each.key} className="scrub-tab" onClick={() => setTab(each.key)}>
              {each.label}
              {each.key === 'skills' && <span className="scrub-tab-count">{measured.activations.length} · ← →</span>}
              {each.key === 'conversation' && <span className="scrub-tab-count">{session.prompts.length}</span>}
            </button>
          ))}
          <span className="scrub-tabs-note">{range === null ? 'Reading the whole session' : `Reading ${format.duration(range[1] - range[0])} in view`}</span>
        </div>
        <div className="scrub-dock-body" role="tabpanel">
          {tab === 'trace' && <ScrubTrace session={session} stepId={place.step} range={range} onSelect={selectStepById} onRange={brush} />}
          {tab === 'skills' && <ScrubSkills session={session} activations={measured.activations} chosen={place.activation} tip={tip} onChoose={chooseActivation} onStep={selectStepById} />}
          {tab === 'conversation' && <ScrubConversation session={session} exchanges={measured.exchanges} range={range} onRange={brush} onStep={selectStepById} />}
          {tab === 'time' && <ScrubTime parts={inView.split.parts} kinds={inView.split.kinds} wallMs={summary.wallMs} whole={whole} />}
          {tab === 'context' && (
            <ScrubContext
              session={session}
              points={measured.context}
              activations={measured.activations}
              range={range}
              cursor={cursor}
              selected={place.step}
              tip={tip}
              onCursor={moveCursor}
              onSelect={selectStep}
            />
          )}
        </div>
      </section>

      <SessionTip tip={tipState.tip} />
    </div>
  );
}

export function ScrubVariant({ view }: { view: SessionView }) {
  const [railOpen, setRailOpen] = useState(true);

  return (
    <div className={`scrub${railOpen ? '' : ' is-rail-shut'}`}>
      <ScrubRail view={view} open={railOpen} onToggle={() => setRailOpen(!railOpen)} />
      {view.session === null ? <ScrubPicker view={view} /> : <SessionPane key={view.session.id} view={view} session={view.session} />}
    </div>
  );
}
