// PROTOTYPE — throwaway. The sticky bar that steps through skill calls, and the card that sums up the one chosen.

import { memo, useEffect } from 'react';
import { format, type Activation } from '../sessionMeasures';

const base = (path: string) => path.split(/[\\/]/).pop() ?? path;

export const SkillCalls = memo(function SkillCalls({ acts, current, onChoose }: { acts: Activation[]; current: number | null; onChoose: (index: number | null) => void }) {
  const chosen = current === null ? null : (acts[current] ?? null);

  const step = (by: number) => {
    if (acts.length === 0) return;
    const next = current === null ? (by > 0 ? 0 : acts.length - 1) : (current + by + acts.length) % acts.length;
    onChoose(next);
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest('input, textarea, select, [contenteditable]') || event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      if (acts.length === 0) return;
      event.preventDefault();
      step(event.key === 'ArrowRight' ? 1 : -1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  return (
    <div className="story-skills">
      <div className="story-pill" role="group" aria-label="Skill calls">
        <span className="story-micro">Skill calls</span>
        <button type="button" onClick={() => step(-1)} disabled={acts.length === 0} aria-label="Previous skill call">
          ◂
        </button>
        <span className="story-pill-now" aria-live="polite">
          {acts.length === 0 ? 'none fired' : chosen === null ? `${acts.length} in this session` : `${chosen.index + 1} of ${acts.length} · ${chosen.step.skill}`}
        </span>
        <button type="button" onClick={() => step(1)} disabled={acts.length === 0} aria-label="Next skill call">
          ▸
        </button>
        {acts.length > 0 && <span className="story-pill-keys">← →</span>}
        <ol className="story-pill-dots" aria-hidden="true">
          {acts.map((act) => (
            <li key={act.index} className={act.index === current ? 'is-on' : undefined} title={act.step.skill} />
          ))}
        </ol>
      </div>

      {chosen !== null && (
        <section className="story-act-card" aria-label={`Skill call ${chosen.index + 1}`}>
          <header>
            <strong>{chosen.step.skill}</strong>
            <span>
              {format.trigger(chosen.step.trigger)}
              {chosen.calledFrom !== null && ` · from ${chosen.calledFrom}`} · prompt {chosen.prompt.index + 1}
            </span>
            <button type="button" className="story-close" onClick={() => onChoose(null)} aria-label="Close the skill call">
              ×
            </button>
          </header>
          <dl>
            <div>
              <dt>Window</dt>
              <dd>
                {format.clock(chosen.startMs, true)} → {format.clock(chosen.endMs, true)} · {format.duration(chosen.endMs - chosen.startMs)}
              </dd>
            </div>
            <div>
              <dt>Cost</dt>
              <dd>{format.usd(chosen.costUsd)}</dd>
            </div>
            <div>
              <dt>Model calls</dt>
              <dd>{chosen.modelCalls}</dd>
            </div>
            <div>
              <dt>Tool calls</dt>
              <dd>{chosen.toolCalls}</dd>
            </div>
            <div className={chosen.failedTools > 0 ? 'is-failed' : undefined}>
              <dt>Failed</dt>
              <dd>{chosen.failedTools}</dd>
            </div>
            <div>
              <dt>Subagents</dt>
              <dd>{chosen.subagents}</dd>
            </div>
          </dl>
          {chosen.files.length > 0 && (
            <p className="story-act-files">
              <span className="story-micro">Edited</span>{' '}
              {chosen.files.slice(0, 4).map((file) => (
                <span key={file.file} title={file.file}>
                  {base(file.file)} <b>{file.edits}×</b>
                </span>
              ))}
            </p>
          )}
        </section>
      )}
    </div>
  );
});
