import { createBrowserRouter } from 'react-router';
import { Activation } from './activations/routes/Activation';
import { Activations } from './activations/routes/Activations';
import { Home } from './skills/routes/Home';

export const router = createBrowserRouter([
  { path: '/', element: <Home /> },
  // The skill is a path segment rather than a filter, so coming back from here cannot hand the
  // reader a table narrowed to a skill they never chose.
  { path: '/skills/:skill/activations', element: <Activations /> },
  { path: '/activations/:id', element: <Activation /> },
]);
