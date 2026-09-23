import { createBrowserRouter } from 'react-router';
import { Home } from './shared/home/routes/Home';
import { home, sessions, watch } from './shared/pages/lib/pages';
import { NoSuchPage } from './shared/pages/routes/NoSuchPage';
import { Session } from './sessions/routes/Session';
import { Sessions } from './sessions/routes/Sessions';
import { Watch } from './watch/routes/Watch';

export const router = createBrowserRouter([
  { path: home.address, element: <Home /> },
  { path: watch.address, element: <Watch /> },
  { path: sessions.address, element: <Sessions /> },
  { path: `${sessions.address}/:id`, element: <Session /> },
  // Author, Test and Publish have no route yet, so their addresses land here too.
  { path: '*', element: <NoSuchPage /> },
]);
