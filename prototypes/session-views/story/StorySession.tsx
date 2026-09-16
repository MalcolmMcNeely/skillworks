// PROTOTYPE — throwaway. One session as a story: a sentence, the findings, then the chapters with the minimap beside them.

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { Session, SessionStep } from '../sessionModel';
import {
  activations,
  contextSeries,
  conversation,
  findings,
  format,
  repositoryLabel,
  sessionName,
  summarize,
  timeSplit,
  type Description,
} from '../sessionMeasures';
import { SessionTip, useTip } from '../SessionTip';
import type { SessionView } from '../useSessionView';
import { ContextCharts, TimeBars } from './StoryCharts';
import { StoryChapter, type PromptFacts } from './StoryChapter';
import { StoryMinimap } from './StoryMinimap';
import { SkillCalls } from './StorySkills';

type ShowTip = (description: Description, event: { clientX: number; clientY: number }, hint?: string | null) => void;

// The sticky skill bar covers the top of the window, and grows when a skill call's card is open, so a chapter under
// it does not count as read and a jump lands below it.
const coveredTop = () => (document.querySelector('.story-skills')?.getBoundingClientRect().bottom ?? 0) + 8;
// Once a jump lands, the bar is stuck to the top, so its height is what covers the target.
const stuckHeight = () => (document.querySelector('.story-skills')?.getBoundingClientRect().height ?? 0) + 8;

function scrollToElement(element: Element | null, behavior: ScrollBehavior = 'smooth') {
  if (element === null) return;
  window.scrollTo({ top: window.scrollY + element.getBoundingClientRect().top - stuckHeight(), behavior });
}

function scrollToMoment(session: Session, ms: number) {
  const span = session.prompts.findLast((each) => each.startMs <= ms) ?? session.prompts[0];
  if (span === undefined) return;
  const element = document.getElementById(`story-chapter-${span.index}`);
  if (element === null) return;
  const rect = element.getBoundingClientRect();
  const share = span.endMs > span.startMs ? Math.min(1, Math.max(0, (ms - span.startMs) / (span.endMs - span.startMs))) : 0;
  window.scrollTo({ top: window.scrollY + rect.top + share * Math.max(0, rect.height - 200) - stuckHeight(), behavior: 'smooth' });
}

export function StorySession({ view, session }: { view: SessionView; session: Session }) {
  const { place, now } = view;

  const measures = useMemo(() => {
    const exchanges = conversation(session);
    const facts = new Map<number, PromptFacts>();
    const steps = new Map<number, SessionStep[]>();
    for (const step of session.steps) {
      if (step.prompt < 0) continue;
      steps.set(step.prompt, [...(steps.get(step.prompt) ?? []), step]);
      const fact = facts.get(step.prompt) ?? { costUsd: 0, calls: 0, tools: 0, failed: 0 };
      if (step.kind === 'model') {
        fact.costUsd += step.costUsd;
        fact.calls += 1;
      }
      if (step.kind === 'tool') fact.tools += 1;
      if ((step.kind === 'tool' && !step.ok) || step.kind === 'modelError' || step.kind === 'rejected') fact.failed += 1;
      facts.set(step.prompt, fact);
    }
    return {
      summary: summarize(session),
      split: timeSplit(session),
      context: contextSeries(session),
      acts: activations(session),
      exchanges,
      found: findings(session),
      facts,
      steps,
    };
  }, [session]);

  const { summary, split, context, acts, exchanges, found } = measures;

  const tipApi = useTip();
  const tipRef = useRef(tipApi);
  const goRef = useRef(view.go);
  useLayoutEffect(() => {
    tipRef.current = tipApi;
    goRef.current = view.go;
  });

  // Stable, so the chapters can skip re-rendering while a hover card moves.
  const showTip = useCallback<ShowTip>((description, event, hint = 'Click for the trace') => tipRef.current.show(description, event, hint), []);
  const hideTip = useCallback(() => tipRef.current.hide(), []);
  const openStep = useCallback((step: SessionStep) => {
    tipRef.current.hide();
    goRef.current({ prompt: step.prompt, step: step.id });
  }, []);
  const closeTrace = useCallback(() => goRef.current({ step: null }), []);
  const jumpTo = useCallback(
    (ms: number) => {
      const span = session.prompts.findLast((each) => each.startMs <= ms);
      if (span !== undefined) goRef.current({ prompt: span.index });
      scrollToMoment(session, ms);
    },
    [session],
  );
  const chooseActivation = useCallback((index: number | null) => {
    if (index === null) {
      goRef.current({ activation: null });
      return;
    }
    const act = measures.acts[index];
    goRef.current({ activation: index, prompt: act.step.prompt });
    // After the card renders, since the card itself changes how much of the window the sticky bar covers.
    setTimeout(() => scrollToElement(document.getElementById(`story-activation-${index}`)), 60);
  }, [measures]);

  const [visible, setVisible] = useState<[number, number] | null>(null);

  useEffect(() => {
    let frame = 0;
    const measure = () => {
      const chapters = [...document.querySelectorAll<HTMLElement>('[data-story-prompt]')];
      const covered = coveredTop();
      let from = Infinity;
      let to = -Infinity;
      for (const element of chapters) {
        const rect = element.getBoundingClientRect();
        if (rect.bottom < covered || rect.top > window.innerHeight) continue;
        const span = session.prompts[Number(element.dataset.storyPrompt)];
        if (span === undefined) continue;
        const length = span.endMs - span.startMs;
        const top = Math.min(1, Math.max(0, (covered - rect.top) / Math.max(1, rect.height)));
        const bottom = Math.min(1, Math.max(0, (window.innerHeight - rect.top) / Math.max(1, rect.height)));
        from = Math.min(from, span.startMs + top * length);
        to = Math.max(to, span.startMs + bottom * length);
      }
      setVisible((last) => (Number.isFinite(from) ? (last !== null && last[0] === from && last[1] === to ? last : [from, to]) : null));
    };
    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    onScroll();
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, [session]);

  // Arriving from another variant, the address says where the reader was; land there once, then leave the scroll alone.
  const landed = useRef(false);
  useLayoutEffect(() => {
    if (landed.current) return;
    landed.current = true;
    const target =
      place.step !== null
        ? document.getElementById('story-trace')
        : place.activation !== null
          ? document.getElementById(`story-activation-${place.activation}`)
          : place.prompt !== null
            ? document.getElementById(`story-chapter-${place.prompt}`)
            : null;
    if (target === null) window.scrollTo(0, 0);
    else scrollToElement(target, 'instant');
  });

  const focusStep = place.step === null ? null : (session.steps.find((step) => step.id === place.step) ?? null);
  const parts = split.parts.toSorted((a, b) => b.ms - a.ms);
  const largest = parts[0];
  const busiest = parts.find((part) => part.key !== 'yourTurn' && part.key !== 'quiet');
  const lastStep = session.steps[session.steps.length - 1];

  const phrase: Record<string, string> = {
    waiting: 'waiting for someone to allow a tool',
    tool: 'tools running',
    hook: 'hooks',
    model: 'the model thinking',
    subagent: 'subagents, with the main thread waiting on them',
    side: 'side requests',
    quiet: 'quiet stretches mid-prompt',
    yourTurn: 'your turn',
  };
  const what = session.title !== null ? `“${session.title}”` : sessionName(session);
  const sentence = [
    `${session.person} ran ${what} in ${repositoryLabel(session.repository)} for ${format.duration(summary.wallMs)}${session.running ? ', and it is still running' : ''}.`,
    `${summary.prompts} prompt${summary.prompts === 1 ? '' : 's'}, ${summary.mainCalls + summary.otherCalls} model calls, ${summary.toolCalls} tool calls and ${format.usd(summary.costUsd)}.`,
    largest.key === 'yourTurn' || largest.key === 'quiet'
      ? `Most of it was ${phrase[largest.key]} (${format.duration(largest.ms)}). Of the busy ${format.duration(summary.busyMs)}, most went to ${phrase[busiest?.key ?? 'model']} (${format.duration(busiest?.ms ?? 0)}).`
      : `Most of the time went to ${phrase[largest.key]} (${format.duration(largest.ms)}).`,
  ].join(' ');

  const figures: [string, string, string?][] = [
    ['Length', format.duration(summary.wallMs)],
    ['Busy', format.duration(summary.busyMs)],
    ['Cost', format.usd(summary.costUsd)],
    ['Prompts', String(summary.prompts)],
    ['Model calls', `${summary.mainCalls} + ${summary.otherCalls}`],
    ['Tool calls', String(summary.toolCalls)],
    ['Failed', String(summary.failedTools + summary.apiErrors + summary.rejected), summary.failedTools + summary.apiErrors + summary.rejected > 0 ? 'is-failed' : undefined],
    ['Skills fired', String(summary.skills.length)],
    ['Peak context', `${format.tokens(summary.peakContext)} · ${format.percent(summary.peakContext / session.contextLimit)}`],
  ];

  return (
    <div className="story-session">
      <nav className="story-crumbs" aria-label="Where you are">
        <button type="button" className="story-link" onClick={() => view.go({ session: null, prompt: null, step: null, activation: null })}>
          ← Sessions in {repositoryLabel(session.repository)}
        </button>
        <span className="story-faint">/</span>
        <span>{session.person}</span>
        <span className="story-faint">/</span>
        <span className="story-fig">
          {format.day(session.startMs)} {format.clock(session.startMs)}
        </span>
      </nav>

      <header className="story-head">
        <h1>{sessionName(session)}</h1>
        {session.running && <span className="story-badge is-live">running · last step {format.ago(lastStep?.at ?? now, now)}</span>}
        <span className="story-badge">{session.entry === 'scripted' ? 'claude -p' : 'interactive'}</span>
        <span className="story-micro">
          Claude Code {session.version} · {session.terminal} · {session.id.slice(0, 8)}
        </span>
      </header>

      <p className="story-sentence">{sentence}</p>

      <dl className="story-figures">
        {figures.map(([label, value, tone]) => (
          <div key={label} className={tone}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>

      {(!session.switches.prompts || !session.switches.responses || !session.switches.toolContent) && (
        <div className="story-withheld story-withheld-note">
          <span>This repository keeps the words out of the store. Lengths, tools and timings still arrive.</span>
          <code>{[!session.switches.prompts && 'OTEL_LOG_USER_PROMPTS', !session.switches.responses && 'OTEL_LOG_ASSISTANT_RESPONSES', !session.switches.toolContent && 'OTEL_LOG_TOOL_CONTENT'].filter(Boolean).join(' · ')}</code>
        </div>
      )}

      {found.length > 0 && (
        <ul className="story-findings" aria-label="Findings">
          {found.map((finding) => {
            const first = session.steps.find((step) => step.id === finding.stepIds[0]);
            return (
              <li key={finding.key} className={`is-${finding.tone}`}>
                <span className="story-finding-mark" aria-hidden="true">
                  {finding.tone === 'failed' ? '◆' : finding.tone === 'warned' ? '▲' : '●'}
                </span>
                <span className="story-finding-title">{finding.title}</span>
                <span className="story-finding-detail">{finding.detail}</span>
                {first !== undefined && (
                  <button type="button" className="story-link" onClick={() => openStep(first)}>
                    {finding.stepIds.length > 1 ? `First of ${finding.stepIds.length} →` : 'Show →'}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <div className="story-columns">
        <div className="story-transcript">
          <SkillCalls acts={acts} current={place.activation} onChoose={chooseActivation} />
          {exchanges.map((exchange) => (
            <StoryChapter
              key={exchange.span.index}
              session={session}
              exchange={exchange}
              steps={measures.steps.get(exchange.span.index) ?? []}
              facts={measures.facts.get(exchange.span.index) ?? { costUsd: 0, calls: 0, tools: 0, failed: 0 }}
              acts={acts}
              currentActivation={place.activation}
              focusStepId={focusStep !== null && focusStep.prompt === exchange.span.index ? focusStep.id : null}
              last={exchange.span.index === session.prompts.length - 1}
              now={now}
              onOpen={openStep}
              onClose={closeTrace}
              onChooseActivation={chooseActivation}
              showTip={showTip}
              hideTip={hideTip}
            />
          ))}
        </div>

        <aside className="story-side" aria-label="The whole session">
          <StoryMinimap session={session} visible={visible} focusStepId={focusStep?.id ?? null} activation={place.activation === null ? null : (acts[place.activation] ?? null)} onOpen={openStep} onJump={jumpTo} showTip={showTip} hideTip={hideTip} />
          <TimeBars split={split} wallMs={summary.wallMs} />
          <ContextCharts session={session} points={context} acts={acts} focusStepId={focusStep?.id ?? null} onOpen={openStep} showTip={showTip} hideTip={hideTip} />
        </aside>
      </div>

      <SessionTip tip={tipApi.tip} />
    </div>
  );
}
