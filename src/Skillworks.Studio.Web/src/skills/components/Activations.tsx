import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { describeCount } from '../../figures/lib/figures';
import { everything, filterParams, readFilter, type Filter } from '../../shared/filters/lib/filters';
import { SignalWord } from '../../shared/gaps/components/SignalWord';
import { missingWords } from '../../shared/gaps/lib/gaps';
import { describeFetchFailure } from '../../http/lib/errors';
import { triggerMark } from '../../shared/provenance/lib/triggers';
import { nowhere, sessionAddress } from '../../shared/session/lib/where';
import { fetchActivations } from '../api/activations';
import {
  describeFiredAt,
  firedInNoRun,
  foldActivationsLine,
  noActivations,
  type Activation,
  type ActivationsAnswer,
} from '../lib/activations';

// A busy skill fires hundreds of times a week, and a reader opens one run at a time.
const mostRows = 20;

interface Reading {
  // The skill and span the answer was asked for, as text, so the list can tell an answer for an older ask.
  asked: string;
  answer: ActivationsAnswer;
  failure: string | null;
}

// Only the span: the run behind an Activation is one run, so a Repository could only narrow it away.
function addressOf(activation: Activation, filter: Filter): string {
  return sessionAddress(activation.session, nowhere, filterParams({ ...everything, from: filter.from, to: filter.to }));
}

export function Activations({ skill, filter }: { skill: string; filter: Filter }) {
  const [reading, setReading] = useState<Reading | null>(null);
  const narrowing = filterParams({ ...filter, skill }).toString();

  useEffect(() => {
    const abort = new AbortController();

    const read = async () => {
      let answer = noActivations;

      // Read back out of the text, so the effect depends only on what it is keyed on.
      for await (const line of fetchActivations(readFilter(new URLSearchParams(narrowing)), abort.signal)) {
        answer = foldActivationsLine(answer, line);
        setReading({ asked: narrowing, answer, failure: null });
      }
    };

    read().catch((failure: unknown) => {
      // An abort is the panel tidying up after itself, not a failure worth showing.
      if (!abort.signal.aborted) {
        setReading({ asked: narrowing, answer: noActivations, failure: describeFetchFailure(failure) });
      }
    });

    return () => abort.abort();
  }, [narrowing]);

  const forOlderAsk = reading !== null && reading.asked !== narrowing;
  const answer = forOlderAsk ? noActivations : (reading?.answer ?? noActivations);
  const failure = forOlderAsk ? null : (reading?.failure ?? null);
  const busy = failure === null && !answer.landed;
  const shown = answer.activations.slice(0, mostRows);

  return (
    <section className="activations" aria-label={`Runs ${skill} fired in`} aria-busy={busy}>
      <span className="activations-label" aria-hidden="true">
        {skill}
      </span>

      {/* Beside the list, so a store that fell short never reads as a skill that fired in no run. */}
      <SignalWord gap={answer.gap} failure={failure} />

      {busy ? (
        <p className="micro activations-word">Reading the activations…</p>
      ) : shown.length === 0 ? (
        <p className="micro activations-word">
          {firedInNoRun(answer) ? 'This skill fired in no run over this span.' : missingWords.noAnswer}
        </p>
      ) : (
        <ul>
          {shown.map((activation) => (
            <li key={`${activation.session}:${activation.atUtc}`} className="activation">
              <Link to={addressOf(activation, filter)}>
                <span className="activation-clock">{describeFiredAt(activation.atUtc)}</span>
                <span className="activation-where">{activation.repository ?? missingWords.none}</span>
                <span className="activation-trigger" aria-hidden="true">
                  {triggerMark(activation.trigger).glyph}
                </span>
                <span className="visually-hidden">{triggerMark(activation.trigger).word}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {answer.activations.length > mostRows ? (
        <p className="micro activations-word">
          The latest {describeCount(mostRows)} of {describeCount(answer.activations.length)} are listed. Narrow the span to
          reach the rest.
        </p>
      ) : null}
    </section>
  );
}
