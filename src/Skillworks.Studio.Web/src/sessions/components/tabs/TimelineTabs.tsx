import { useState } from 'react';
import type { Range } from '../../lib/view';
import type { ActivationSpell } from '../../lib/panels/activations';
import type { Level } from '../../lib/panels/context';
import { ContextTab } from './ContextTab';
import { SkillsTab } from './SkillsTab';

type TabKey = 'context' | 'skills';

const tabs: readonly { key: TabKey; label: string }[] = [
  { key: 'context', label: 'Context' },
  { key: 'skills', label: 'Skills' },
];

export function TimelineTabs({
  levels,
  limitTokens,
  spells,
  view,
  selected,
  opened,
  onOpen,
  onActivation,
}: {
  levels: readonly Level[];
  limitTokens: number | null;
  spells: readonly ActivationSpell[];
  view: Range | null;
  selected: string | null;
  opened: string | null;
  onOpen: (step: string) => void;
  onActivation: (spell: ActivationSpell) => void;
}) {
  const [shown, setShown] = useState<TabKey>('context');

  return (
    <section className="session-panel timeline-tabs" aria-label="What is in view">
      <div className="tab-row" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            id={`tab-${tab.key}`}
            aria-selected={tab.key === shown}
            aria-controls={`tab-panel-${tab.key}`}
            className={`tab${tab.key === shown ? ' is-shown' : ''}`}
            onClick={() => setShown(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="tab-panel" role="tabpanel" id={`tab-panel-${shown}`} aria-labelledby={`tab-${shown}`}>
        {shown === 'context' ? (
          <ContextTab levels={levels} limitTokens={limitTokens} view={view} selected={selected} onOpen={onOpen} />
        ) : (
          <SkillsTab spells={spells} view={view} opened={opened} onOpen={onActivation} />
        )}
      </div>
    </section>
  );
}
