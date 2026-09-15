import { createBrowserRouter } from 'react-router';
import { Home } from './skills/routes/Home';

export const router = createBrowserRouter([{ path: '/', element: <Home /> }]);
