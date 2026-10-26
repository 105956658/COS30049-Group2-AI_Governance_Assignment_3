/**
 * detector.js – the two calls the UI makes. Components import from here, never from
 * client.js or mock.js directly, so switching between the real back end and demo mode
 * (VITE_USE_MOCK) changes nothing else.
 *
 *   GET  /api/health   → { status: 'ok', model_loaded: true, model_version: '…' }
 *   POST /api/predict  { text } → PredictResponse (see README, "API contract")
 */
import { apiFetch } from './client.js';
import { USE_MOCK } from '../config.js';
import { mockHealth, mockPredict } from './mock.js';

export function getHealth({ signal } = {}) {
  return USE_MOCK ? mockHealth() : apiFetch('/api/health', { signal, timeout: 5000 });
}

export function predict(text, { signal } = {}) {
  return USE_MOCK
    ? mockPredict(text, { signal })
    : apiFetch('/api/predict', { method: 'POST', body: { text }, signal });
}

export function predictFile(file, { signal } = {}) {
  const formData = new FormData();
  formData.append('file', file);

  return apiFetch('/api/predict-file', {
    method: 'POST',
    body: formData,
    signal,
  });
}