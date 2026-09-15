export interface Origin {
  trigger: string | null;
  source: string | null;
  plugin: string | null;
  marketplace: string | null;
}

export interface TriggerCount {
  // Null where the firing was recorded without one, as an older Claude Code sends no trigger.
  trigger: string | null;
  activations: number;
}
