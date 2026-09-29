// PROTOTYPE — throwaway. Reads the detail behind each Step straight from Loki and Tempo, through the dev server's
// proxy, so the drawer can be judged on real runs before the API carries any of it.
import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { Mark } from '../../lib/steps';

export interface HookRun {
  event: string;
  hooks: number;
  ms: number;
}

export interface TurnDetail {
  kind: 'turn';
  source: string | null;
  model: string | null;
  effort: string | null;
  speed: string | null;
  inputTokens: number;
  outputTokens: number;
  cacheRead: number;
  cacheWrite: number;
  cost: number;
  ms: number;
  firstWordMs: number | null;
  stopReason: string | null;
  attempt: number | null;
}

export interface ToolDetail {
  kind: 'tool';
  tool: string;
  success: boolean | null;
  error: string | null;
  input: Record<string, unknown> | null;
  parameters: Record<string, unknown> | null;
  resultBytes: number | null;
  decision: string | null;
  decisionSource: string | null;
  waitedMs: number | null;
  ranMs: number | null;
  ms: number;
  output: string | null;
  diff: string | null;
  content: string | null;
  commandClass: string | null;
  hooks: HookRun[];
}

export type StepDetail = TurnDetail | ToolDetail;

export interface Details {
  byStep: ReadonlyMap<string, StepDetail>;
  events: 'reading' | 'read' | 'failed';
  spans: 'reading' | 'read' | 'failed';
}

const nothing: Details = { byStep: new Map(), events: 'reading', spans: 'reading' };

export const DetailsContext = createContext<Details>(nothing);

export function useDetail(id: string | null): StepDetail | null {
  const details = useContext(DetailsContext);

  return id === null ? null : (details.byStep.get(id) ?? null);
}

export function useDetailsState(): Details {
  return useContext(DetailsContext);
}

type Labels = Record<string, string>;

interface Event {
  labels: Labels;
  atMs: number;
  sequence: number;
}

interface SpanEvent {
  name: string;
  attributes: Record<string, string>;
}

interface Span {
  id: string;
  parent: string | null;
  name: string;
  attributes: Record<string, string>;
  events: SpanEvent[];
}

const eventNames = ['api_request', 'tool_result', 'tool_decision', 'hook_execution_complete'];

function number(value: string | undefined): number | null {
  if (value === undefined || value === '') {
    return null;
  }

  const read = Number(value);

  return Number.isFinite(read) ? read : null;
}

function json(value: string | undefined): Record<string, unknown> | null {
  if (value === undefined || value === '') {
    return null;
  }

  try {
    const read: unknown = JSON.parse(value);

    return read !== null && typeof read === 'object' ? (read as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

async function readEvents(session: string, fromMs: number, toMs: number): Promise<Event[]> {
  const query = `{service_name=~".+"} | session_id="${session}" | event_name=~"${eventNames.join('|')}"`;
  const params = new URLSearchParams({
    query,
    start: `${Math.floor(fromMs) * 1_000_000}`,
    end: `${Math.ceil(toMs) * 1_000_000}`,
    limit: '5000',
    direction: 'forward',
  });
  const answer = await fetch(`/pp-loki/loki/api/v1/query_range?${params.toString()}`);

  if (!answer.ok) {
    throw new Error(`Loki said ${answer.status}`);
  }

  const read = (await answer.json()) as { data: { result: { stream: Labels; values: [string, string][] }[] } };

  return read.data.result.flatMap((stream) =>
    stream.values.map(([at]) => ({
      labels: stream.stream,
      atMs: Date.parse(stream.stream.event_timestamp ?? '') || Number(BigInt(at) / 1_000_000n),
      sequence: Number(stream.stream.event_sequence ?? -1),
    })),
  );
}

function valueOf(value: Record<string, unknown> | undefined): string {
  if (value === undefined) {
    return '';
  }

  const inner = Object.values(value)[0];

  return typeof inner === 'object' ? JSON.stringify(inner) : String(inner);
}

function attributesOf(list: { key: string; value: Record<string, unknown> }[] | undefined): Record<string, string> {
  return Object.fromEntries((list ?? []).map((each) => [each.key, valueOf(each.value)]));
}

async function readSpans(session: string, traces: readonly string[]): Promise<Span[]> {
  const read = await Promise.all(
    traces.map(async (trace) => {
      const answer = await fetch(`/pp-tempo/api/traces/${trace}`);

      if (!answer.ok) {
        return [];
      }

      const body = (await answer.json()) as {
        batches?: {
          scopeSpans?: {
            spans: {
              spanId: string;
              parentSpanId?: string;
              name: string;
              attributes?: { key: string; value: Record<string, unknown> }[];
              events?: { name: string; attributes?: { key: string; value: Record<string, unknown> }[] }[];
            }[];
          }[];
        }[];
      };

      return (body.batches ?? []).flatMap((batch) =>
        (batch.scopeSpans ?? []).flatMap((scope) =>
          scope.spans.map((span) => ({
            id: span.spanId,
            parent: span.parentSpanId ?? null,
            name: span.name,
            attributes: attributesOf(span.attributes),
            events: (span.events ?? []).map((event) => ({ name: event.name, attributes: attributesOf(event.attributes) })),
          })),
        ),
      );
    }),
  );

  // A spec loop's own runs share the trace, so only this run's spans are kept.
  return read.flat().filter((span) => span.attributes['session.id'] === session);
}

// Step ids are Claude Code's event numbers, which start again when Claude Code restarts, so the nearest in time wins.
function eventFor(events: readonly Event[], mark: Mark, name: string): Event | null {
  const endMs = mark.startMs + mark.step.lengthMs;
  let found: Event | null = null;

  for (const event of events) {
    if (String(event.sequence) === mark.step.id && event.labels.event_name === name) {
      if (found === null || Math.abs(event.atMs - endMs) < Math.abs(found.atMs - endMs)) {
        found = event;
      }
    }
  }

  return found;
}

function hooksAround(events: readonly Event[], result: Event, tool: string): HookRun[] {
  const near = events.filter(
    (event) =>
      event.labels.event_name === 'hook_execution_complete' &&
      Math.abs(event.sequence - result.sequence) <= 8 &&
      Math.abs(event.atMs - result.atMs) < 120_000,
  );
  const before = near
    .filter((event) => event.labels.hook_name === `PreToolUse:${tool}` && event.sequence < result.sequence)
    .toSorted((one, other) => other.sequence - one.sequence)[0];
  const after = near
    .filter((event) => event.labels.hook_name === `PostToolUse:${tool}` && event.sequence > result.sequence)
    .toSorted((one, other) => one.sequence - other.sequence)[0];

  return [before, after]
    .filter((event) => event !== undefined)
    .map((event) => ({
      event: event.labels.hook_event ?? '',
      hooks: number(event.labels.num_hooks) ?? 0,
      ms: number(event.labels.total_duration_ms) ?? 0,
    }));
}

function turnOf(event: Event, spans: readonly Span[]): TurnDetail {
  const labels = event.labels;
  const span = spans.find((each) => each.name === 'claude_code.llm_request' && each.attributes.request_id === labels.request_id);

  return {
    kind: 'turn',
    source: labels.query_source ?? null,
    model: span?.attributes.model ?? labels.model ?? null,
    effort: labels.effort ?? null,
    speed: labels.speed ?? null,
    inputTokens: number(labels.input_tokens) ?? 0,
    outputTokens: number(labels.output_tokens) ?? 0,
    cacheRead: number(labels.cache_read_tokens) ?? 0,
    cacheWrite: number(labels.cache_creation_tokens) ?? 0,
    cost: number(labels.cost_usd) ?? 0,
    ms: number(labels.duration_ms) ?? 0,
    firstWordMs: number(labels.ttft_ms),
    stopReason: span?.attributes.stop_reason ?? null,
    attempt: number(span?.attributes.attempt),
  };
}

function toolOf(event: Event, events: readonly Event[], spans: readonly Span[]): ToolDetail {
  const labels = event.labels;
  const tool = labels.tool_name ?? '';
  const use = labels.tool_use_id;
  const decided = events.find((each) => each.labels.event_name === 'tool_decision' && each.labels.tool_use_id === use);
  const span = spans.find((each) => each.name === 'claude_code.tool' && each.attributes.tool_use_id === use);
  const child = (name: string) => spans.find((each) => each.parent === span?.id && each.name === name);
  const executed = child('claude_code.tool.execution');
  const blocked = child('claude_code.tool.blocked_on_user');
  const said = span?.events.find((each) => each.name === 'tool.output')?.attributes ?? {};

  return {
    kind: 'tool',
    tool,
    success: labels.success === undefined ? null : labels.success === 'true',
    error: labels.error ?? executed?.attributes.error ?? null,
    input: json(labels.tool_input),
    parameters: json(labels.tool_parameters ?? decided?.labels.tool_parameters),
    resultBytes: number(labels.tool_result_size_bytes),
    decision: labels.decision_type ?? decided?.labels.decision ?? null,
    decisionSource: labels.decision_source ?? decided?.labels.source ?? null,
    waitedMs: number(blocked?.attributes.duration_ms),
    ranMs: number(executed?.attributes.duration_ms),
    ms: number(labels.duration_ms) ?? 0,
    output: said.output ?? null,
    diff: said.diff ?? null,
    content: said.content ?? null,
    commandClass: span?.attributes.bash_command_class ?? null,
    hooks: hooksAround(events, event, tool),
  };
}

function detailsOf(marks: readonly Mark[], events: readonly Event[], spans: readonly Span[]): Map<string, StepDetail> {
  const byStep = new Map<string, StepDetail>();

  for (const mark of marks) {
    if (mark.step.kind === 'turn') {
      const event = eventFor(events, mark, 'api_request');

      if (event !== null) {
        byStep.set(mark.step.id, turnOf(event, spans));
      }
    } else if (mark.step.kind === 'tool') {
      const event = eventFor(events, mark, 'tool_result');

      if (event !== null) {
        byStep.set(mark.step.id, toolOf(event, events, spans));
      }
    }
  }

  return byStep;
}

interface Read {
  events: Event[];
  spans: Span[];
  eventsState: Details['events'];
  spansState: Details['spans'];
}

const unread: Read = { events: [], spans: [], eventsState: 'reading', spansState: 'reading' };

// Read once per run: the marks only say where to look, and a View change must not read the stores again.
export function useStepDetails(session: string | null, marks: readonly Mark[]): Details {
  const [read, setRead] = useState<Read>(unread);
  const fromMs = marks.length === 0 ? null : Math.min(...marks.map((mark) => mark.startMs)) - 60_000;
  const toMs = marks.length === 0 ? null : Math.max(...marks.map((mark) => mark.endMs)) + 60_000;

  useEffect(() => {
    if (session === null || fromMs === null || toMs === null) {
      return;
    }

    let live = true;

    void (async () => {
      let events: Event[];

      try {
        events = await readEvents(session, fromMs, toMs);
      } catch {
        if (live) {
          setRead({ ...unread, eventsState: 'failed', spansState: 'failed' });
        }

        return;
      }

      if (live) {
        setRead({ events, spans: [], eventsState: 'read', spansState: 'reading' });
      }

      const traces = [...new Set(events.map((event) => event.labels.trace_id).filter((trace) => trace !== undefined))];

      try {
        const spans = await readSpans(session, traces);

        if (live) {
          setRead({ events, spans, eventsState: 'read', spansState: 'read' });
        }
      } catch {
        if (live) {
          setRead({ events, spans: [], eventsState: 'read', spansState: 'failed' });
        }
      }
    })();

    return () => {
      live = false;
    };
  }, [session, fromMs, toMs]);

  return useMemo(
    () => ({ byStep: detailsOf(marks, read.events, read.spans), events: read.eventsState, spans: read.spansState }),
    [marks, read],
  );
}
