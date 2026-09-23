import { isValidElement } from 'react';
import { matchRoutes } from 'react-router';
import { describe, expect, it } from 'vitest';
import { routes } from './routes';
import { Home } from './shared/home/routes/Home';
import { dashboard, home } from './shared/pages/lib/pages';
import { NoSuchPage } from './shared/pages/routes/NoSuchPage';
import { Dashboard } from './watch/routes/Dashboard';

function screenAt(address: string): unknown {
  const element = matchRoutes(routes, address)?.at(-1)?.route.element;

  return isValidElement(element) ? element.type : undefined;
}

describe('routes', () => {
  it('opens Home at the plain address', () => {
    expect(screenAt(home.address)).toBe(Home);
  });

  it('opens the Dashboard at its own address', () => {
    expect(screenAt('/dashboard')).toBe(Dashboard);
    expect(screenAt(dashboard.address)).toBe(Dashboard);
  });

  it('sends the old Watch address nowhere, so the page has one name', () => {
    expect(screenAt('/watch')).toBe(NoSuchPage);
  });
});
