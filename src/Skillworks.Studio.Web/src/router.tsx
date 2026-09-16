import { createBrowserRouter, replace } from 'react-router';
import { home, watch } from './pages/lib/pages';
import { Watch } from './skills/routes/Watch';

export const router = createBrowserRouter([
  {
    path: home.address,
    // A push would send the back button into the redirect again.
    loader: ({ request }) => replace(`${watch.address}${new URL(request.url).search}`),
  },
  { path: watch.address, element: <Watch /> },
]);
