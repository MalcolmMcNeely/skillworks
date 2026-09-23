import type { RouteObject } from 'react-router';
import { Home } from './shared/home/routes/Home';
import { dashboard, home, sessions } from './shared/pages/lib/pages';
import { NoSuchPage } from './shared/pages/routes/NoSuchPage';
import { Session } from './sessions/routes/Session';
import { Sessions } from './sessions/routes/Sessions';
import { Dashboard } from './watch/routes/Dashboard';

// Apart from the router, because a browser router cannot be built where a test runs.
export const routes: RouteObject[] = [
  { path: home.address, element: <Home /> },
  { path: dashboard.address, element: <Dashboard /> },
  { path: sessions.address, element: <Sessions /> },
  { path: `${sessions.address}/:id`, element: <Session /> },
  // Author, Test and Publish have no route yet, so their addresses land here too.
  { path: '*', element: <NoSuchPage /> },
];
