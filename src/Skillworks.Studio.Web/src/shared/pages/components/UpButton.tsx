import { Link } from 'react-router';
import type { Page } from '../lib/pages';

// A link, not the browser's back: a page opened from a bookmark has no Studio page behind it.
// The query is what the page above was asked for, so going up lands on the list a reader left, not a fresh one.
export function UpButton({ parent, query = '' }: { parent: Page; query?: string }) {
  return (
    <Link className="up" to={query === '' ? parent.address : `${parent.address}?${query}`}>
      <span className="up-chevron" aria-hidden="true">
        ‹
      </span>
      {parent.name}
    </Link>
  );
}
