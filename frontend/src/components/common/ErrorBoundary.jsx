/**
 * ErrorBoundary – catches errors thrown while rendering anything inside it and shows
 * a fallback page instead of a blank screen (adapted from the Week 8 React Showcase).
 *
 * Error boundaries still need a class component: no hook replaces getDerivedStateFromError.
 * The fallback deliberately does NOT print error.message – internal details stay in the
 * console for developers, the user gets a plain explanation and a way out.
 */
import { Component } from 'react';
import { TriangleAlert } from 'lucide-react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught an error:', error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="error-page" role="alert">
        <TriangleAlert size={48} className="error-page-icon" aria-hidden="true" />
        <p className="eyebrow">Unexpected error</p>
        <h1>Something went wrong on this page</h1>
        <p className="muted">
          Reloading usually fixes it. Checks you already made in this tab are kept and will still be listed
          after the reload.
        </p>
        <div className="row">
          <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>
            Reload the page
          </button>
          {/* A plain <a>, not <Link>: this fallback may render outside the router. */}
          <a href="/" className="btn">
            Go to the detector
          </a>
        </div>
      </div>
    );
  }
}
