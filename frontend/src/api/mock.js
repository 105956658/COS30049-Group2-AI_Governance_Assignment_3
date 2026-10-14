/**
 * mock.js – DEMO responses so the UI can be built and tested before the back end exists.
 * Only used when VITE_USE_MOCK=true; the header shows a "Demo data" badge while it is on.
 * The scores come from a crude word-pattern heuristic, NOT the trained model.
 *
 * Responses follow the same contract as the real API, including errors, so every
 * loading / success / error state in the UI can be exercised.
 */
import { ApiError } from './client.js';
import { AI_THRESHOLD, MAX_CHARS, MIN_WORDS, countWords } from '../config.js';

function wait(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => {
      clearTimeout(timer);
      reject(signal.reason ?? new DOMException('Aborted', 'AbortError'));
    });
  });
}

// Same sentence split as features.py: after . ! ? (plus closing quotes/brackets) or at a newline.
const SPLIT = /(?<=[.!?])["')\]]*\s+|\n+/;
const AI_MARKERS =
  /\b(moreover|furthermore|additionally|overall|crucial|delve|ensure|various|significant|enhance|landscape|in conclusion|it is important)\b/gi;

function sentenceScore(sentence) {
  const words = sentence.split(/\s+/);
  const markers = (sentence.match(AI_MARKERS) ?? []).length;
  const avgLen = words.reduce((n, w) => n + w.length, 0) / words.length;
  const raw = -1.2 + markers * 1.1 + (avgLen - 4.6) * 0.9 + (words.length > 18 ? 0.5 : 0);
  return 1 / (1 + Math.exp(-raw));
}

export async function mockHealth() {
  await wait(150);
  return { status: 'ok', model_loaded: true, model_version: 'demo' };
}

export async function mockPredict(text, { signal } = {}) {
  await wait(500 + Math.random() * 600, signal);

  // Typing "#error" or "#busy" in the text shows those error states without a back end.
  const fail = (status, code, message) => new ApiError(message, { status, code, details: [] });
  if (text.includes('#error')) throw fail(500, 'internal_error', 'The server hit an unexpected problem. Please try again.');
  if (text.includes('#busy')) throw fail(503, 'server_busy', 'The service is busy right now. Please try again in a few seconds.');
  if (text.length > MAX_CHARS) throw fail(413, 'text_too_long', `Text must be at most ${MAX_CHARS} characters.`);
  if (countWords(text) < MIN_WORDS) throw fail(422, 'text_too_short', `Text must contain at least ${MIN_WORDS} words.`);

  const sentences = text
    .trim()
    .split(SPLIT)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => ({ text: s, p_ai: s.split(/\s+/).length >= 4 ? sentenceScore(s) : null }));
  const scored = sentences.filter((s) => s.p_ai !== null).map((s) => s.p_ai);
  const mean = scored.reduce((a, b) => a + b, 0) / Math.max(scored.length, 1);
  const spread = 0.08 + 0.25 / Math.sqrt(Math.max(scored.length, 1));
  const aiScore = Math.min(0.99, Math.max(0.01, mean));
  const label = aiScore >= AI_THRESHOLD ? 'ai' : 'human';

  return {
    label,
    confidence: label === 'ai' ? aiScore : 1 - aiScore,
    ai_score: aiScore,
    score_range: { low: Math.max(0, aiScore - spread), high: Math.min(1, aiScore + spread) },
    sentences,
    word_count: countWords(text),
    model_version: 'demo',
  };
}
