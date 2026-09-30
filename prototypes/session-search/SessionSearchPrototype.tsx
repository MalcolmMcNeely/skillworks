// PROTOTYPE: throwaway. Three variants of a search box on the existing /sessions route, switched by ?variant=.
// Question: what should a search by Session id look like, given the reader already knows the id?
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { clock } from '../../shared/clock/lib/clock';
import { everything, type Filter } from '../../shared/filters/lib/filters';
import { nowhere, sessionAddress } from '../../shared/session/lib/where';
import { fetchSession } from '../api/sessions';
import { describeRunLength, describeStarted, noRepository, notKnown, type Session, type SessionsAnswer } from '../lib/sessions';
import { SessionTable } from './SessionTable';

export const searchVariants = [
  { key: 'A', name: 'Jump box: Enter opens the run' },
  { key: 'B', name: 'Narrow the list as you type, box on the right' },
  { key: 'C', name: 'Palette with a preview (press /)' },
] as const;

const boxStyle = {
  font: 'inherit',
  padding: '4px 8px',
  minWidth: '22rem',
  border: '1px solid var(--rule, #555)',
  background: 'transparent',
  color: 'inherit',
} as const;

function StateLine({ state }: { state: Record<string, unknown> }) {
  return (
    <pre style={{ fontSize: 11, opacity: 0.6, margin: '4px 0' }}>PROTOTYPE state: {JSON.stringify(state)}</pre>
  );
}

// A: a plain box, across from the Repository picker. Enter goes straight to the run's page, which reads one id and nothing else.
export function VariantA() {
  const navigate = useNavigate();
  const [typed, setTyped] = useState('');
  const id = typed.trim();

  return (
    <form
        onSubmit={(event) => {
          event.preventDefault();
          if (id !== '') navigate(sessionAddress(id, nowhere, new URLSearchParams()));
        }}
        style={{ display: 'flex', gap: 8, alignItems: 'center', marginLeft: 'auto' }}
        title={`PROTOTYPE state: ${JSON.stringify({ typed: id })}`}
      >
        <input
          aria-label="Session id"
          placeholder="Paste a Session id and press Enter"
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
          style={boxStyle}
        />
        <button type="submit" disabled={id === ''}>
          Open
        </button>
      </form>
  );
}

// B: the box sits across from the Repository picker and narrows the rows already read, by id prefix.
// The reader picks a run from the list, so an id that names no run never reaches the run's page.
export function VariantBBox({ typed, onType }: { typed: string; onType: (typed: string) => void }) {
  return (
    <input
      aria-label="Session id"
      placeholder="Type the start of a Session id"
      value={typed}
      onChange={(event) => onType(event.target.value)}
      style={{ ...boxStyle, marginLeft: 'auto' }}
    />
  );
}

// A whole id is the one case the loaded rows cannot answer for an older run, so only it goes to the store.
const wholeId = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

type Lookup =
  | { id: string; state: 'found'; session: Session; ms: number }
  | { id: string; state: 'missing'; ms: number }
  | { id: string; state: 'failed'; reason: string };

export function VariantB({
  typed,
  answer,
  failure,
  filter,
  onReadOn,
}: {
  typed: string;
  answer: SessionsAnswer | null;
  failure: string | null;
  filter: Filter;
  onReadOn: () => void;
}) {
  const id = typed.trim().toLowerCase();
  const [lookup, setLookup] = useState<Lookup | null>(null);

  const narrowed =
    answer === null || id === ''
      ? answer
      : { ...answer, rows: answer.rows.filter((row) => row.session.id.toLowerCase().startsWith(id)) };

  const loaded = answer?.rows.length ?? 0;
  const matched = narrowed?.rows.length ?? 0;
  const askStore = wholeId.test(id) && matched === 0;

  // Only the head line is wanted, so the read stops as soon as it lands.
  useEffect(() => {
    if (!askStore) {
      return;
    }
    const abort = new AbortController();
    const began = clock().now();

    const read = async () => {
      for await (const line of fetchSession(id, { from: everything.from, to: everything.to }, abort.signal)) {
        if (line.kind === 'head') {
          const ms = clock().now() - began;
          setLookup(line.session === null ? { id, state: 'missing', ms } : { id, state: 'found', session: line.session, ms });
          abort.abort();
          return;
        }
      }
    };
    read().catch((fault: unknown) => {
      if (!abort.signal.aborted) setLookup({ id, state: 'failed', reason: String(fault) });
    });
    return () => abort.abort();
  }, [askStore, id]);

  const landed = lookup !== null && lookup.id === id ? lookup : null;

  return (
    <>
      <StateLine
        state={{
          typed: id,
          loaded,
          matched,
          askStore,
          lookup: askStore ? (landed === null ? 'reading' : landed.state) : null,
          ms: landed !== null && 'ms' in landed ? landed.ms : null,
        }}
      />
      {id === '' || matched > 0 ? (
        <SessionTable answer={narrowed} failure={failure} filter={filter} onReadOn={onReadOn} />
      ) : !askStore ? (
        <p className="session-word">
          No run in the {loaded} rows read so far starts with “{typed.trim()}”. Paste the whole id to look further back.
        </p>
      ) : landed === null ? (
        <p className="session-word">Not in the {loaded} newest runs. Looking further back…</p>
      ) : landed.state === 'missing' ? (
        <p className="session-word">No run has that id ({landed.ms} ms).</p>
      ) : landed.state === 'failed' ? (
        <p className="session-word">{landed.reason}</p>
      ) : (
        <table className="sessions-table">
          <tbody>
            <tr>
              <td className="session-started">{describeStarted(landed.session.startedUtc)}</td>
              <td>{landed.session.repository ?? noRepository}</td>
              <td>{landed.session.person ?? notKnown}</td>
              <td className="session-name">
                <Link to={sessionAddress(landed.session.id, nowhere, new URLSearchParams())}>{landed.session.name}</Link>
              </td>
              <td className="session-figure">{describeRunLength(landed.session.lengthMs)}</td>
              <td className="session-word">found further back in {landed.ms} ms</td>
            </tr>
          </tbody>
        </table>
      )}
    </>
  );
}

type Preview =
  | { state: 'idle' }
  | { state: 'reading'; id: string }
  | { state: 'found'; id: string; session: Session; ms: number }
  | { state: 'missing'; id: string; ms: number }
  | { state: 'failed'; id: string; reason: string };

// C: the list stays clean. "/" opens a palette; a pasted id shows the run's head before the reader commits.
export function VariantC({ table }: { table: React.ReactNode }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState('');
  const [preview, setPreview] = useState<Preview>({ state: 'idle' });
  const box = useRef<HTMLInputElement>(null);
  const id = typed.trim();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const inBox = (event.target as HTMLElement | null)?.closest('input, textarea') !== null;
      if (event.key === '/' && !inBox) {
        event.preventDefault();
        setOpen(true);
      }
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (open) box.current?.focus();
  }, [open]);

  // Only the head line is wanted, so the read stops as soon as it lands.
  useEffect(() => {
    if (id === '') {
      return;
    }
    const abort = new AbortController();
    const began = clock().now();

    const read = async () => {
      for await (const line of fetchSession(id, { from: everything.from, to: everything.to }, abort.signal)) {
        if (line.kind === 'head') {
          const ms = Math.round(clock().now() - began);
          setPreview(line.session === null ? { state: 'missing', id, ms } : { state: 'found', id, session: line.session, ms });
          abort.abort();
          return;
        }
      }
    };
    read().catch((failure: unknown) => {
      if (!abort.signal.aborted) setPreview({ state: 'failed', id, reason: String(failure) });
    });
    return () => abort.abort();
  }, [id]);

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} style={{ alignSelf: 'flex-start' }}>
        Find a Session by id <kbd>/</kbd>
      </button>
      {table}
      {open ? (
        <div
          onClick={() => setOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,.55)',
            display: 'flex',
            justifyContent: 'center',
            paddingTop: '15vh',
            zIndex: 900,
          }}
        >
          <div
            onClick={(event) => event.stopPropagation()}
            style={{
              background: 'var(--ground, #1b1b1b)',
              border: '1px solid var(--rule, #555)',
              padding: 16,
              width: 'min(36rem, 92vw)',
              height: 'fit-content',
            }}
          >
            <form
              onSubmit={(event) => {
                event.preventDefault();
                if (preview.state === 'found') navigate(sessionAddress(preview.id, nowhere, new URLSearchParams()));
              }}
            >
              <input
                ref={box}
                aria-label="Session id"
                placeholder="Paste a Session id"
                value={typed}
                onChange={(event) => {
                  setTyped(event.target.value);
                  const next = event.target.value.trim();
                  setPreview(next === '' ? { state: 'idle' } : { state: 'reading', id: next });
                }}
                style={{ ...boxStyle, width: '100%', minWidth: 0 }}
              />
            </form>
            <div style={{ marginTop: 12, minHeight: '3rem' }}>
              {preview.state === 'reading' ? <p className="session-word">Looking…</p> : null}
              {preview.state === 'missing' ? (
                <p className="session-word">No run with that id ({preview.ms} ms).</p>
              ) : null}
              {preview.state === 'failed' ? <p className="session-word">{preview.reason}</p> : null}
              {preview.state === 'found' ? (
                <button
                  type="button"
                  onClick={() => navigate(sessionAddress(preview.id, nowhere, new URLSearchParams()))}
                  style={{ width: '100%', textAlign: 'left' }}
                >
                  <strong>{preview.session.name}</strong>
                  <br />
                  {preview.session.repository ?? 'None'} · {preview.session.person ?? 'Not known'} ·{' '}
                  {preview.session.startedUtc} · found in {preview.ms} ms — Enter to open
                </button>
              ) : null}
            </div>
            <StateLine state={{ typed: id, preview: preview.state }} />
          </div>
        </div>
      ) : null}
    </>
  );
}
