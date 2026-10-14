import { Suspense } from 'react';
import { Outlet, useLocation } from 'react-router-dom';

import Header from './Header.jsx';
import Footer from './Footer.jsx';
import ErrorBoundary from '../common/ErrorBoundary.jsx';
import PageLoader from '../common/PageLoader.jsx';

/**
 * Layout – the frame around every page: skip link, header, main area, footer.
 *
 * The ErrorBoundary is keyed by the URL, so after a page crashes, navigating to
 * another page clears the error instead of leaving the fallback stuck on screen.
 */
export default function Layout() {
  const { pathname } = useLocation();

  return (
    <div className="app">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <Header />
      <main id="main" className="main" tabIndex={-1}>
        <ErrorBoundary key={pathname}>
          <Suspense fallback={<PageLoader />}>
            <Outlet />
          </Suspense>
        </ErrorBoundary>
      </main>
      <Footer />
    </div>
  );
}
