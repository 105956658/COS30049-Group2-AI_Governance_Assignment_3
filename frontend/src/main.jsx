/**
 * main.jsx – entry point. Wraps the app in its providers and mounts it in <div id="root">.
 *
 * The outer ErrorBoundary is the last line of defence: if anything outside a page
 * crashes (the header, a provider…), the user still gets a page, never a blank screen.
 */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import App from './App.jsx';
import ErrorBoundary from './components/common/ErrorBoundary.jsx';
import { ThemeProvider } from './context/ThemeContext.jsx';
import './index.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <ThemeProvider>
          <App />
        </ThemeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);
