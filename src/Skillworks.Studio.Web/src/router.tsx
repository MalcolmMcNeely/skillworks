import { createBrowserRouter, replace } from 'react-router';
import { Home } from './home/routes/Home';
import { oldLinkRedirect } from './pages/lib/oldLinks';
import { home, watch } from './pages/lib/pages';
import { NoSuchPage } from './pages/routes/NoSuchPage';
import { Watch } from './skills/routes/Watch';

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
  // Author, Test and Publish have no route yet, so their addresses land here too.
  { path: '*', element: <NoSuchPage /> },
]);
