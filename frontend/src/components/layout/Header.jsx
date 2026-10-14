import { NavLink } from 'react-router-dom';
import { Moon, ScanText, Sun } from 'lucide-react';

import { useTheme } from '../../context/ThemeContext.jsx';
import useBackendStatus from '../../hooks/useBackendStatus.js';
import { USE_MOCK } from '../../config.js';

const STATUS_TEXT = {
  checking: 'Connecting…',
  online: 'Model online',
  offline: 'Service offline',
};

export default function Header() {
  const { theme, toggleTheme } = useTheme();
  const status = useBackendStatus();

  return (
    <header className="header">
      <div className="header-inner">
        <NavLink to="/" className="brand" aria-label="TextTrace home">
          <ScanText size={24} aria-hidden="true" />
          <span>TextTrace</span>
        </NavLink>

        <nav aria-label="Main" className="nav">
          <NavLink to="/" end className="nav-link">
            Detector
          </NavLink>
          <NavLink to="/about" className="nav-link">
            How it works
          </NavLink>
        </nav>

        <div className="header-actions">
          {USE_MOCK && (
            <span className="badge badge-warning" title="Results come from src/api/mock.js, not the trained model">
              Demo data
            </span>
          )}
          <span className={`status-pill status-${status}`} role="status">
            <span className="status-dot" aria-hidden="true" />
            <span className="status-text">{STATUS_TEXT[status]}</span>
          </span>
          <button
            type="button"
            className="btn-icon"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </div>
    </header>
  );
}
