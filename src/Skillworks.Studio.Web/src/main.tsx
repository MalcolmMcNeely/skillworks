import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router/dom';
import { paletteProperties } from './shared/palette/lib/palette';
import { router } from './router';
import './styles.css';

for (const [name, colour] of Object.entries(paletteProperties)) {
  document.documentElement.style.setProperty(name, colour);
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
