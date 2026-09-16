import { createBrowserRouter } from 'react-router';
import { Home } from './skills/routes/Home';

export const router = createBrowserRouter([
  { path: '/', element: <Home /> },
  // PROTOTYPE — the session view variants. Development builds only, and loaded only when opened.
  ...(import.meta.env.DEV
    ? [
        {
          path: '/prototype/sessions',
          lazy: async () => ({ Component: (await import('./sessions/prototype/SessionsPrototype')).SessionsPrototype }),
        },
      ]
    : []),
]);
