/**
 * config.js – limits and thresholds shared by the whole front end.
 *
 * The input limits are for USABILITY only: they stop the user sending something the
 * back end will refuse anyway. The back end must enforce the same limits itself,
 * because an attacker can skip this UI and call the API directly with curl.
 */

// The pipeline only scores sentences with >= 4 words (MIN_WORDS in features.py),
// so very short inputs give the model almost nothing to work with.
export const MIN_WORDS = 20;
export const MAX_CHARS = 10_000;

// The regressor outputs P(AI) for the whole document; at or above this it is labelled AI.
// 0.5 is the threshold used when the model was evaluated (acc@0.5 in regressor.py).
export const AI_THRESHOLD = 0.5;

// Number of checks kept in this browser tab's history (for the comparison chart).
export const MAX_HISTORY = 30;

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

/** Words the way a person counts them: runs of non-space characters. */
export function countWords(text) {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

/**
 * Front-end validation. Returns an error message, or null when the text is fine.
 * Mirrors the rules the back end applies, so the user hears about a problem
 * before the request is sent.
 */
export function validateText(text) {
  if (!text.trim()) return 'Paste or type some text to check.';
  if (text.length > MAX_CHARS) {
    return `Text is too long: ${text.length.toLocaleString()} characters (maximum ${MAX_CHARS.toLocaleString()}).`;
  }
  const words = countWords(text);
  if (words < MIN_WORDS) {
    return `Text is too short: ${words} word${words === 1 ? '' : 's'} (minimum ${MIN_WORDS}). Short texts do not carry enough signal for a reliable result.`;
  }
  return null;
}
