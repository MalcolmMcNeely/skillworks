import { createBrowserRouter } from 'react-router';
import { Activation } from './activations/routes/Activation';
import { Activations } from './activations/routes/Activations';
import { Home } from './skills/routes/Home';

export const router = createBrowserRouter([
  { path: '/', element: <Home /> },
  // The skill is a path segment, not a filter, so coming back never leaves the table narrowed to it.
  { path: '/skills/:skill/activations', element: <Activations /> },
  { path: '/activations/:id', element: <Activation /> },
]);
