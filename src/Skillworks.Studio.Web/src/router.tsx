import { createBrowserRouter } from 'react-router';
import { Home } from './routes/Home';

export const router = createBrowserRouter([{ path: '/', element: <Home /> }]);
