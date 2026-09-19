import { createBrowserRouter, replace } from 'react-router';
import { Home } from './shared/home/routes/Home';
import { oldLinkRedirect } from './shared/pages/lib/oldLinks';
import { home, sessions, watch } from './shared/pages/lib/pages';
import { NoSuchPage } from './shared/pages/routes/NoSuchPage';
import { Session } from './sessions/routes/Session';
import { Sessions } from './sessions/routes/Sessions';
import { Watch } from './watch/routes/Watch';

export const router = createBrowserRouter([
  {
    path: home.address,
    loader: ({ request }) => {
      const onward = oldLinkRedirect(new URL(request.url).search);

      // A push would send the back button into the redirect again.
      return onward === null ? null : replace(onward);
    },
    element: <Home />,
  },
  { path: watch.address, element: <Watch /> },
  { path: sessions.address, element: <Sessions /> },
  { path: `${sessions.address}/:id`, element: <Session /> },
  // Author, Test and Publish have no route yet, so their addresses land here too.
  { path: '*', element: <NoSuchPage /> },
]);
