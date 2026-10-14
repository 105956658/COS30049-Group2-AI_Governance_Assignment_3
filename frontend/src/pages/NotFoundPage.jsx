import { Link, useLocation } from 'react-router-dom';
import { Compass } from 'lucide-react';
import useDocumentTitle from '../hooks/useDocumentTitle.js';

/** Shown for any address that does not match a route (path="*" in App.jsx). */
export default function NotFoundPage() {
  const { pathname } = useLocation();
  useDocumentTitle('Page not found');

  return (
    <div className="error-page">
      <Compass size={48} className="error-page-icon" aria-hidden="true" />
      <p className="eyebrow">Error 404</p>
      <h1>This page does not exist</h1>
      {/* pathname is rendered as text, so a crafted URL cannot inject HTML here. */}
      <p className="muted">
        Nothing lives at <code>{pathname}</code>. Check the address, or head back to the detector.
      </p>
      <Link to="/" className="btn btn-primary">
        Go to the detector
      </Link>
    </div>
  );
}
