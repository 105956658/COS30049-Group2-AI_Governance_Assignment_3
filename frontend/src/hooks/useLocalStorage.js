import { useEffect, useState } from 'react';

/**
 * useLocalStorage – works exactly like useState, but the value is also saved
 * in the browser's localStorage, so it survives a page refresh.
 *
 *   const [name, setName] = useLocalStorage('name', 'Guest');
 *
 * This is a "custom hook": a normal function whose name starts with `use`
 * and which calls other hooks inside it.
 */
export default function useLocalStorage(key, initialValue) {
  // Passing a function to useState means this code only runs on the first render.
  const [value, setValue] = useState(() => {
    try {
      const saved = window.localStorage.getItem(key);
      return saved !== null ? JSON.parse(saved) : initialValue;
    } catch {
      return initialValue; // storage blocked (e.g. private mode) or invalid JSON
    }
  });

  // Whenever the value changes, write it back to storage.
  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Ignore write errors – the app still works, it just won't remember.
    }
  }, [key, value]);

  return [value, setValue];
}
