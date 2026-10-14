import { useCallback, useEffect, useState } from 'react';
import { MAX_HISTORY } from '../config.js';

const KEY = 'texttrace-history';

function load() {
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(KEY));
    return Array.isArray(saved) ? saved : [];
  } catch {
    return []; // storage blocked (private mode) or corrupted – start empty
  }
}

/**
 * useSessionHistory – every check made in this browser tab, newest last.
 *
 * Kept in sessionStorage (not localStorage) on purpose: the texts people check can be
 * private, so the history is forgotten when the tab closes and is never sent anywhere.
 *
 *   const { history, addCheck, clearHistory } = useSessionHistory();
 */
export default function useSessionHistory() {
  const [history, setHistory] = useState(load);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(KEY, JSON.stringify(history));
    } catch {
      // Ignore – the app still works, the history just will not survive a refresh.
    }
  }, [history]);

  const addCheck = useCallback((text, result) => {
    const entry = {
      id: crypto.randomUUID(),
      checkedAt: new Date().toISOString(),
      text,
      result,
    };
    setHistory((current) => [...current, entry].slice(-MAX_HISTORY));
    return entry;
  }, []);

  const clearHistory = useCallback(() => setHistory([]), []);

  return { history, addCheck, clearHistory };
}
