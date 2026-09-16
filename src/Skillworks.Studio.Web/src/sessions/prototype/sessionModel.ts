// PROTOTYPE — throwaway. The shape one session takes once Loki's events and Tempo's spans are joined.
// It assumes traces are on everywhere, so every step knows its parent span.

export type Thread = 'main' | 'subagent' | 'side';

export type ToolFamily = 'shell' | 'edit' | 'read' | 'agent' | 'skill' | 'other';

export type Trigger = 'user-slash' | 'claude-proactive' | 'nested-skill' | 'agent-preload';

// The three settings that decide whether the words themselves reach the store. Off, only lengths arrive.
export interface ContentSwitches {
  prompts: boolean;
  responses: boolean;
  toolContent: boolean;
}

export interface Said {
  text: string | null;
  length: number;
}

interface Step {
  id: string;
  // The span this step sits under: the prompt for main-thread work, a subagent for its own work, a tool for its hooks.
  parent: string | null;
  prompt: number;
  // Claude Code writes an event when its step ends, so the start is always worked back from the duration.
  at: number;
  ms: number;
  agent: string | null;
}

export interface PromptStep extends Step {
  kind: 'prompt';
  said: Said;
  command: string | null;
}

export interface ModelStep extends Step {
  kind: 'model';
  thread: Thread;
  // The subagent type, or what a side request was for, such as naming the session.
  purpose: string;
  querySource: string;
  model: string;
  effort: string;
  ttftMs: number;
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheCreationTokens: number;
  costUsd: number;
  skill: string | null;
  stopReason: 'tool_use' | 'end_turn' | 'max_tokens';
  attempt: number;
  requestId: string;
  said: Said | null;
  toolUseIds: string[];
}

export interface ModelErrorStep extends Step {
  kind: 'modelError';
  model: string;
  status: number;
  message: string;
  attempt: number;
}

export interface ToolStep extends Step {
  kind: 'tool';
  tool: string;
  family: ToolFamily;
  ok: boolean;
  errorType: string | null;
  error: string | null;
  summary: string;
  input: string;
  output: string | null;
  inputBytes: number;
  outputBytes: number;
  // Time spent waiting for the developer to allow it, before it ran.
  waitedMs: number;
  allowedBy: string;
  toolUseId: string;
}

export interface RejectedStep extends Step {
  kind: 'rejected';
  tool: string;
  source: string;
  summary: string;
}

export interface HookStep extends Step {
  kind: 'hook';
  hook: string;
  hooks: number;
  blocking: number;
  errors: number;
}

export interface SkillStep extends Step {
  kind: 'skill';
  skill: string;
  trigger: Trigger;
  source: string;
  plugin: string | null;
}

export interface SubagentStep extends Step {
  kind: 'subagent';
  agentType: string;
  description: string;
  agentId: string;
  model: string;
  tokens: number;
  toolUses: number;
  async: boolean;
}

export type SessionStep =
  | PromptStep
  | ModelStep
  | ModelErrorStep
  | ToolStep
  | RejectedStep
  | HookStep
  | SkillStep
  | SubagentStep;

export interface PromptSpan {
  index: number;
  stepId: string;
  startMs: number;
  endMs: number;
}

export interface Session {
  id: string;
  repository: string;
  person: string;
  startMs: number;
  endMs: number;
  running: boolean;
  entry: 'interactive' | 'scripted';
  version: string;
  terminal: string;
  // Named by a side request to a small model, so it is withheld along with every other response.
  title: string | null;
  switches: ContentSwitches;
  contextLimit: number;
  prompts: PromptSpan[];
  steps: SessionStep[];
}
