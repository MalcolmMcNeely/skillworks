// PROTOTYPE — throwaway. What one Turn or Tool call says about itself, in a brief form and a full one.
// Every variant places these differently; the words inside them are the part already agreed.
import type { ReactNode } from 'react';
import { describeCount, describeLength, describeMoney, describeTokens } from '../../../shared/figures/lib/figures';
import { ranBy } from '../../lib/timeline/agents';
import { describeClock, titleOf, type Mark } from '../../lib/steps';
import { useDetail, useDetailsState, type HookRun, type StepDetail, type ToolDetail, type TurnDetail } from './stepDetails';

// Claude Code cuts a Span's output here, so a reader must be told the text stops short.
const outputCut = 2048;

export function whyItRan(source: string | null): string {
  if (source === null) {
    return 'Not known';
  }

  if (source.startsWith('repl_')) {
    return 'Work on the Prompt';
  }

  if (source.startsWith('agent')) {
    return 'Subagent work';
  }

  const known: Record<string, string> = {
    away_summary: 'Recap while you were away',
    prompt_suggestion: 'Next-prompt suggestion',
    generate_session_title: 'Session title',
    compact: 'Compaction',
    auto_compact: 'Compaction',
  };

  return known[source] ?? source;
}

// Only work on the Prompt is what the reader asked for; the rest is Claude Code's own upkeep.
export function isUpkeep(detail: TurnDetail): boolean {
  return detail.source !== null && !detail.source.startsWith('repl_') && !detail.source.startsWith('agent');
}

function stopWords(reason: string | null): string | null {
  const known: Record<string, string> = {
    end_turn: 'Finished its reply',
    tool_use: 'Asked for a tool',
    max_tokens: 'Cut off at the output limit',
    stop_sequence: 'Hit a stop sequence',
    refusal: 'Refused',
    pause_turn: 'Paused',
  };

  return reason === null ? null : (known[reason] ?? reason);
}

function approvalWords(detail: ToolDetail): string {
  if (detail.decision === 'reject') {
    return 'Refused';
  }

  const known: Record<string, string> = {
    config: 'Allowed by your settings',
    user_temporary: 'You allowed it, this once',
    user_permanent: 'You allowed it, from now on',
    user_abort: 'You stopped it',
    user_reject: 'You refused it',
    hook: 'A hook allowed it',
    mode: 'Allowed by the permission mode',
  };

  return detail.decisionSource === null ? 'Not known' : (known[detail.decisionSource] ?? detail.decisionSource);
}

function text(fields: Record<string, unknown> | null, key: string): string | null {
  const value = fields?.[key];

  return typeof value === 'string' && value !== '' ? value : null;
}

function shortPath(path: string): string {
  const parts = path.split(/[\\/]/);

  return parts.length <= 3 ? path : `…/${parts.slice(-3).join('/')}`;
}

// One line that says what the call did, so a row or a tip can name it without opening it.
export function whatItDid(detail: ToolDetail): string {
  const input = detail.input;
  const parameters = detail.parameters;
  const command = text(parameters, 'full_command') ?? text(input, 'command');
  const file = text(input, 'file_path') ?? text(input, 'notebook_path');

  switch (detail.tool) {
    case 'Bash':
      return text(parameters, 'description') ?? text(input, 'description') ?? command ?? 'A shell command';
    case 'Edit':
    case 'MultiEdit':
    case 'Write':
    case 'NotebookEdit':
    case 'Read':
      return file === null ? detail.tool : shortPath(file);
    case 'Skill':
      return text(input, 'skill') ?? text(parameters, 'skill_name') ?? 'A skill';
    case 'Grep':
    case 'Glob':
      return text(input, 'pattern') ?? detail.tool;
    case 'Task':
    case 'Agent':
      return text(input, 'description') ?? 'A Subagent';
    default:
      return command ?? file ?? (input === null ? detail.tool : JSON.stringify(input).slice(0, 120));
  }
}

function describeBytes(bytes: number): string {
  return bytes < 1024 ? `${describeCount(bytes)} B` : `${(bytes / 1024).toFixed(1)} KB`;
}

function Split({ parts }: { parts: { label: string; value: number; tone: string; words: string }[] }) {
  const whole = parts.reduce((sum, part) => sum + part.value, 0);

  if (whole <= 0) {
    return null;
  }

  return (
    <div className="pp-split">
      <div className="pp-split-bar" aria-hidden="true">
        {parts
          .filter((part) => part.value > 0)
          .map((part) => (
            <span key={part.label} className={`pp-split-part is-${part.tone}`} style={{ flexGrow: part.value }} />
          ))}
      </div>
      <ul className="pp-split-key">
        {parts.map((part) => (
          <li key={part.label} className={part.value > 0 ? '' : 'is-none'}>
            <span className={`pp-swatch is-${part.tone}`} aria-hidden="true" />
            {part.label} <span className="pp-figure">{part.words}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="pp-row">
      <dt className="micro">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function tokenParts(detail: TurnDetail) {
  return [
    { label: 'Read from cache', value: detail.cacheRead, tone: 'cache', words: describeTokens(detail.cacheRead) },
    { label: 'Written to cache', value: detail.cacheWrite, tone: 'write', words: describeTokens(detail.cacheWrite) },
    { label: 'New input', value: detail.inputTokens, tone: 'input', words: describeTokens(detail.inputTokens) },
    { label: 'Output', value: detail.outputTokens, tone: 'output', words: describeTokens(detail.outputTokens) },
  ];
}

function TurnFull({ detail, spansRead }: { detail: TurnDetail; spansRead: boolean }) {
  const stop = stopWords(detail.stopReason);
  const firstWord = detail.firstWordMs;

  return (
    <dl className="pp-detail">
      <Row label="Why it ran">
        {whyItRan(detail.source)} <code className="pp-raw">{detail.source ?? ''}</code>
      </Row>
      <Row label="Model">
        {detail.model ?? 'Not known'}
        {detail.effort === null ? '' : ` · ${detail.effort} effort`}
        {detail.speed === null || detail.speed === 'normal' ? '' : ` · ${detail.speed}`}
      </Row>
      <Row label="Cost">{describeMoney(detail.cost)}</Row>
      <Row label="Tokens">
        <Split parts={tokenParts(detail)} />
      </Row>
      <Row label="Time">
        <Split
          parts={[
            {
              label: 'Wait for the first word',
              value: firstWord ?? 0,
              tone: 'wait',
              words: firstWord === null ? 'not known' : describeLength(firstWord),
            },
            {
              label: 'Writing',
              value: Math.max(0, detail.ms - (firstWord ?? 0)),
              tone: 'output',
              words: describeLength(Math.max(0, detail.ms - (firstWord ?? 0))),
            },
          ]}
        />
      </Row>
      <Row label="Why it stopped">{stop ?? (spansRead ? 'Not known' : 'Reading the spans…')}</Row>
      {detail.attempt !== null && detail.attempt > 1 ? <Row label="Retries">Attempt {detail.attempt}</Row> : null}
    </dl>
  );
}

function Diff({ diff }: { diff: string }) {
  let hunks: { oldStart: number; lines: string[] }[] | null = null;

  try {
    hunks = JSON.parse(diff) as { oldStart: number; lines: string[] }[];
  } catch {
    hunks = null;
  }

  if (hunks === null) {
    return <pre className="pp-code">{diff}</pre>;
  }

  return (
    <pre className="pp-code pp-diff">
      {hunks.map((hunk) => (
        <span key={hunk.oldStart}>
          <span className="pp-diff-at">@@ line {hunk.oldStart}</span>
          {'\n'}
          {hunk.lines.map((line, index) => (
            <span key={index} className={line.startsWith('+') ? 'is-added' : line.startsWith('-') ? 'is-removed' : ''}>
              {line}
              {'\n'}
            </span>
          ))}
        </span>
      ))}
    </pre>
  );
}

function Asked({ detail }: { detail: ToolDetail }) {
  const input = detail.input;
  const command = text(detail.parameters, 'full_command') ?? text(input, 'command');
  const description = text(detail.parameters, 'description') ?? text(input, 'description');
  const file = text(input, 'file_path') ?? text(input, 'notebook_path');

  if (detail.tool === 'Bash') {
    return (
      <>
        {description === null ? null : <p>{description}</p>}
        {command === null ? <p className="pp-withheld">Withheld</p> : <pre className="pp-code">{command}</pre>}
      </>
    );
  }

  if (file !== null) {
    const oldText = text(input, 'old_string');
    const newText = text(input, 'new_string');

    return (
      <>
        <p className="pp-mono">{file}</p>
        {detail.diff !== null ? (
          <Diff diff={detail.diff} />
        ) : oldText !== null || newText !== null ? (
          <pre className="pp-code pp-diff">
            {oldText === null ? null : <span className="is-removed">{oldText.replace(/^/gm, '-')}</span>}
            {'\n'}
            {newText === null ? null : <span className="is-added">{newText.replace(/^/gm, '+')}</span>}
          </pre>
        ) : null}
      </>
    );
  }

  return input === null ? <p className="pp-withheld">Withheld</p> : <pre className="pp-code">{JSON.stringify(input, null, 2)}</pre>;
}

function GotBack({ detail, spansRead }: { detail: ToolDetail; spansRead: boolean }) {
  const back = detail.output ?? detail.content;
  const cut = back !== null && back.length >= outputCut;

  if (back === null) {
    return (
      <p className="pp-withheld">
        {detail.diff !== null ? 'The change above.' : spansRead ? 'No output was recorded.' : 'Reading the spans…'}
        {detail.resultBytes === null ? '' : ` · ${describeBytes(detail.resultBytes)} in all`}
      </p>
    );
  }

  return (
    <>
      <pre className="pp-code pp-output">{back}</pre>
      <p className="micro">
        {cut ? `The first ${describeCount(outputCut)} characters` : 'All of it'}
        {detail.resultBytes === null ? '' : ` · ${describeBytes(detail.resultBytes)} in all`}
      </p>
    </>
  );
}

function describeHooks(hook: HookRun | undefined): string {
  return hook === undefined ? 'none' : `${describeLength(hook.ms)} · ${hook.hooks} ${hook.hooks === 1 ? 'hook' : 'hooks'}`;
}

function toolTimeParts(detail: ToolDetail) {
  const before = detail.hooks.find((hook) => hook.event === 'PreToolUse');
  const after = detail.hooks.find((hook) => hook.event === 'PostToolUse');
  const waited = detail.waitedMs ?? 0;
  const ran = detail.ranMs ?? Math.max(0, detail.ms - waited);

  return [
    { label: 'Hooks before', value: before?.ms ?? 0, tone: 'hook', words: describeHooks(before) },
    { label: 'Waiting for approval', value: waited, tone: 'wait', words: detail.waitedMs === null ? 'not known' : describeLength(waited) },
    { label: 'Running', value: ran, tone: 'output', words: describeLength(ran) },
    { label: 'Hooks after', value: after?.ms ?? 0, tone: 'hook', words: describeHooks(after) },
  ];
}

function ToolFull({ detail, spansRead }: { detail: ToolDetail; spansRead: boolean }) {
  return (
    <dl className="pp-detail">
      <Row label="Result">
        {detail.success === false ? <span className="pp-failed">Failed</span> : detail.success ? 'Passed' : 'Not known'}
        {detail.error === null ? null : <pre className="pp-code pp-error">{detail.error}</pre>}
      </Row>
      <Row label={detail.tool === 'Bash' ? 'Command' : 'Asked for'}>
        <Asked detail={detail} />
      </Row>
      <Row label="Got back">
        <GotBack detail={detail} spansRead={spansRead} />
      </Row>
      <Row label="Approval">
        {approvalWords(detail)}
        {detail.waitedMs !== null && detail.waitedMs > 1000 ? ` · waited ${describeLength(detail.waitedMs)} for you` : ''}
      </Row>
      <Row label="Time">
        <Split parts={toolTimeParts(detail)} />
      </Row>
    </dl>
  );
}

export function DetailFull({ mark, traced, agents }: { mark: Mark; traced: boolean; agents: Record<string, string> }) {
  const detail = useDetail(mark.step.id);
  const state = useDetailsState();

  return (
    <div className="pp-card">
      <p className="step-open-head">
        {titleOf(mark.step)}
        {mark.step.fault ? <span className="step-note">Failed</span> : null}
      </p>
      <p className="micro">
        {describeClock(mark.startMs, true)} · {describeLength(mark.step.lengthMs)} · ran by {ranBy(traced, agents, mark.step.id)}
        {mark.step.skill === null ? '' : ` · ${mark.step.skill}`}
      </p>
      <DetailBody mark={mark} detail={detail} state={state.events} spansRead={state.spans !== 'reading'} />
    </div>
  );
}

function DetailBody({
  mark,
  detail,
  state,
  spansRead,
}: {
  mark: Mark;
  detail: StepDetail | null;
  state: 'reading' | 'read' | 'failed';
  spansRead: boolean;
}) {
  if (mark.step.kind === 'prompt' || mark.step.kind === 'answer') {
    return mark.step.words === null ? null : <p className="step-words">{mark.step.words}</p>;
  }

  if (detail === null) {
    return (
      <p className="pp-withheld">
        {state === 'reading' ? 'Reading the events…' : state === 'failed' ? 'Loki did not answer.' : 'No event matched this Step.'}
      </p>
    );
  }

  return detail.kind === 'turn' ? <TurnFull detail={detail} spansRead={spansRead} /> : <ToolFull detail={detail} spansRead={spansRead} />;
}

// One line, for a row in a list of Steps.
export function DetailLine({ mark }: { mark: Mark }) {
  const detail = useDetail(mark.step.id);

  if (detail === null) {
    return <span className="pp-dim">{mark.step.words ?? ''}</span>;
  }

  if (detail.kind === 'turn') {
    return (
      <span className={isUpkeep(detail) ? 'pp-upkeep' : ''}>
        {whyItRan(detail.source)} · {describeTokens(detail.outputTokens)} out · {describeMoney(detail.cost)}
      </span>
    );
  }

  return (
    <span>
      {detail.success === false ? <span className="pp-failed">Failed · </span> : null}
      {whatItDid(detail)}
    </span>
  );
}

// Two or three lines, for a place with no room: the tip beside the cursor.
export function DetailBrief({ mark }: { mark: Mark }) {
  const detail = useDetail(mark.step.id);

  if (detail === null) {
    return mark.step.words === null ? null : <p className="pp-brief-line">{mark.step.words}</p>;
  }

  if (detail.kind === 'turn') {
    const stop = stopWords(detail.stopReason);

    return (
      <>
        <p className="pp-brief-line">
          <span className={isUpkeep(detail) ? 'pp-upkeep' : ''}>{whyItRan(detail.source)}</span> · {describeMoney(detail.cost)}
          {stop === null ? '' : ` · ${stop}`}
        </p>
        <p className="pp-brief-line pp-dim">
          {describeTokens(detail.outputTokens)} out · {describeTokens(detail.inputTokens + detail.cacheWrite)} new in ·{' '}
          {describeTokens(detail.cacheRead)} from cache
          {detail.firstWordMs === null ? '' : ` · first word ${describeLength(detail.firstWordMs)}`}
        </p>
      </>
    );
  }

  const hooks = detail.hooks.reduce((sum, hook) => sum + hook.ms, 0);

  return (
    <>
      <p className="pp-brief-line">{whatItDid(detail)}</p>
      <p className="pp-brief-line pp-dim">
        {detail.success === false ? <span className="pp-failed">Failed</span> : 'Passed'}
        {detail.resultBytes === null ? '' : ` · ${describeBytes(detail.resultBytes)} back`} · {approvalWords(detail)}
        {hooks > 0 ? ` · hooks ${describeLength(hooks)}` : ''}
      </p>
    </>
  );
}
