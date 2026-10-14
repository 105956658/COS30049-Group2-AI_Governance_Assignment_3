import { useEffect, useState } from 'react';
import { getHealth } from '../api/detector.js';

/**
 * useBackendStatus – asks GET /api/health once when the app opens, so the header can
 * say up front whether checks will work, instead of the user finding out on submit.
 *
 * Returns 'checking' | 'online' | 'offline'.
 */
export default function useBackendStatus() {
  const [status, setStatus] = useState('checking');

  useEffect(() => {
    const controller = new AbortController();
    getHealth({ signal: controller.signal })
      .then((data) => setStatus(data?.model_loaded ? 'online' : 'offline'))
      .catch(() => {
        if (!controller.signal.aborted) setStatus('offline');
      });
    return () => controller.abort();
  }, []);

  return status;
}
