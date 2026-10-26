/**
 * client.js – one wrapper around fetch() for talking to the FastAPI back end
 * (adapted from the COS30049 Week 8 React Showcase).
 *
 * Every error the back end sends uses one JSON shape (see README, "Error format"):
 *
 *   { "error": { "code": "text_too_long", "message": "Text must be at most 10000 characters.",
 *                "details": [{ "field": "text", "message": "…" }] } }
 *
 * This wrapper turns any failure – that shape, FastAPI's default { detail } shape,
 * a timeout, or the back end being offline – into an ApiError with a readable message.
 */

// In development the Vite proxy forwards /api/* to http://127.0.0.1:8000, so the base is empty.
export const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'network_error', details = [] } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status; // 0 = the request never got an HTTP answer (offline / timeout)
    this.code = code;
    this.details = details; // [{ field, message }] for validation errors
  }

  get isOffline() {
    return this.status === 0;
  }

  /** { text: 'message' } – lets a form show the error beside the right field. */
  get fieldErrors() {
    const errors = {};
    for (const d of this.details) if (d.field && !errors[d.field]) errors[d.field] = d.message;
    return errors;
  }
}

const OFFLINE_MESSAGE =
  'Cannot reach the detection service. Check that the back end is running, then try again.';

// Fallbacks when the server sends a status code but no usable message.
const STATUS_MESSAGES = {
  413: 'The text or file is larger than the server accepts.',
  415: 'Unsupported file type or content. Upload a UTF-8 .txt file.',
  422: 'The server could not accept this input.',
  429: 'Too many checks in a short time. Please wait a moment and try again.',
  500: 'The server hit an unexpected problem. Please try again.',
  503: 'The service is busy right now. Please try again in a few seconds.',
};

/** Read an error body, accepting our shared format and FastAPI's default one. */
function toApiError(status, body) {
  if (body?.error) {
    const { code = 'error', message, details = [] } = body.error;
    return new ApiError(message || STATUS_MESSAGES[status] || `Request failed (${status}).`, {
      status,
      code,
      details,
    });
  }
  if (Array.isArray(body?.detail)) {
    // FastAPI's default 422: [{ loc: ['body', 'text'], msg: '…' }]
    const details = body.detail.map((d) => ({ field: d.loc?.[d.loc.length - 1], message: d.msg }));
    return new ApiError(details[0]?.message ?? STATUS_MESSAGES[422], { status, code: 'validation_error', details });
  }
  const message = typeof body?.detail === 'string' ? body.detail : STATUS_MESSAGES[status];
  return new ApiError(message ?? `Request failed (${status}).`, { status, code: `http_${status}` });
}

/**
 * apiFetch(path, { method, body, timeout, signal })
 * `body` is a plain object sent as JSON. `signal` lets the caller cancel the request.
 */
export async function apiFetch(path, { method = 'GET', body, timeout = 20000, signal } = {}) {
  const isFormData = body instanceof FormData;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new DOMException('Timeout', 'TimeoutError')), timeout);
  const onAbort = () => controller.abort(signal.reason);
  signal?.addEventListener('abort', onAbort);

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
    method,
    signal: controller.signal,
    headers: {
      Accept: 'application/json',
      ...(body !== undefined && !isFormData
      ? { 'Content-Type': 'application/json' }
      : {}),
    },
    body: body === undefined
      ? undefined
      : isFormData
        ? body
        : JSON.stringify(body),
    });
  } catch (error) {
    if (signal?.aborted) throw error; // cancelled by the caller, who will ignore it
    if (controller.signal.reason?.name === 'TimeoutError') {
      throw new ApiError(`The server took longer than ${timeout / 1000} s to answer. Please try again.`, {
        code: 'timeout',
      });
    }
    throw new ApiError(OFFLINE_MESSAGE);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', onAbort);
  }

  const isJson = response.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    // The Vite dev proxy answers with an empty, non-JSON 5xx when FastAPI is not running.
    if (!isJson && response.status >= 500 && response.status !== 503) throw new ApiError(OFFLINE_MESSAGE);
    throw toApiError(response.status, data);
  }
  return data;
}
