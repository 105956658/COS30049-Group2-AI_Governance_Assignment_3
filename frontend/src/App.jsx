/**
 * App.jsx – decides which page to show for the current URL.
 * Pages are lazy-loaded, so each one's code is only downloaded when it is first visited.
 */
import { lazy } from 'react';
import { Route, Routes } from 'react-router-dom';

import Layout from './components/layout/Layout.jsx';

const DetectorPage = lazy(() => import('./pages/DetectorPage.jsx'));
const AboutPage = lazy(() => import('./pages/AboutPage.jsx'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage.jsx'));

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DetectorPage />} />
        <Route path="about" element={<AboutPage />} />
        {/* Any other address → 404 page */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
