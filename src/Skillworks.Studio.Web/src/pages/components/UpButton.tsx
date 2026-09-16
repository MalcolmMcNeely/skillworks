import { Link } from 'react-router';
import type { Page } from '../lib/pages';

// A link, not the browser's back: a page opened from a bookmark has no Studio page behind it.
export function UpButton({ parent }: { parent: Page }) {
  return (
    <Link className="up" to={parent.address}>
      <span className="up-chevron" aria-hidden="true">
        ‹
      </span>
      {parent.name}
    </Link>
  );
}
