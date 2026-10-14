/**
 * ThemeContext – shares the current colour theme ("light" or "dark") with
 * every component in the app, without passing it down through props.
 *
 *   1. createContext()   creates the "channel"
 *   2. <ThemeProvider>   puts a value into the channel (see main.jsx)
 *   3. useTheme()        reads the value from any component below it
 */
import { createContext, useContext, useEffect } from 'react';
import useLocalStorage from '../hooks/useLocalStorage.js';

const ThemeContext = createContext(null);

function getPreferredTheme() {
  // Respect the operating-system setting the first time someone visits.
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useLocalStorage('texttrace-theme', getPreferredTheme());

  // Side effect: reflect the theme on <html data-theme="..."> so CSS can use it.
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme() must be used inside <ThemeProvider>');
  return context;
}
