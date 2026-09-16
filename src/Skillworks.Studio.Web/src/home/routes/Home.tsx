import { Link } from 'react-router';
import { HealthLamps } from '../../health/components/HealthLamps';
import { useTabTitle } from '../../pages/components/useTabTitle';
import { home, pagesBelow, type Page } from '../../pages/lib/pages';

function Panel({ page }: { page: Page }) {
  const face = (
    <>
      <span className="home-panel-glyph" aria-hidden="true">
        {page.glyph}
      </span>
      <span className="home-panel-name">{page.name}</span>
    </>
  );

  // A disabled link still takes Tab and still opens, so an unbuilt job gets no link at all.
  if (!page.built) {
    return (
      <li className="home-panel is-unbuilt">
        <div className="home-panel-face">
          {face}
          <span className="micro">Not yet</span>
        </div>
      </li>
    );
  }

  // No search part, so a panel always opens its page with the defaults.
  return (
    <li className="home-panel">
      <Link className="home-panel-face" to={page.address}>
        {face}
      </Link>
    </li>
  );
}

// Health and nothing else: a read of the Events store would open Home on an Arriving answer.
export function Home() {
  useTabTitle(home.tabTitle);

  return (
    <main className="page home">
      <h1>Skillworks</h1>

      <ul className="home-panels" aria-label="Jobs">
        {pagesBelow(home).map((page) => (
          <Panel key={page.address} page={page} />
        ))}
      </ul>

      <section className="home-systems" aria-label="Systems">
        <HealthLamps />
      </section>
    </main>
  );
}
