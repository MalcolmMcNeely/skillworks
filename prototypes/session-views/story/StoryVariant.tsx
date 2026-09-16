// PROTOTYPE — throwaway. Variant C, Story: the conversation comes first, and the whole session rides beside it as a
// vertical minimap. An index of repositories and sessions comes before any session is open.

import type { SessionView } from '../useSessionView';
import { StoryIndex } from './StoryIndex';
import { StorySession } from './StorySession';
import './StoryVariant.css';

export function StoryVariant({ view }: { view: SessionView }) {
  return <div className="story">{view.session === null ? <StoryIndex view={view} /> : <StorySession key={view.session.id} view={view} session={view.session} />}</div>;
}
