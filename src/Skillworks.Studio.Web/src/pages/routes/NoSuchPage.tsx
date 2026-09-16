import { UpButton } from '../components/UpButton';
import { useTabTitle } from '../components/useTabTitle';
import { home, noSuchPageName, tabTitleOf } from '../lib/pages';

export function NoSuchPage() {
  useTabTitle(tabTitleOf(noSuchPageName));

  return (
    <main className="page no-such-page">
      <UpButton parent={home} />
      <h1>{noSuchPageName}</h1>
    </main>
  );
}
