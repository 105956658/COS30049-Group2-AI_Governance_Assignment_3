/** Small display helpers shared by the result card, charts and history list. */
import { AI_THRESHOLD } from '../config.js';

export const VERDICT = {
  ai: { short: 'AI-generated', long: 'Likely AI-generated' },
  human: { short: 'Human-written', long: 'Likely human-written' },
};

/** 0.873 → "87%" */
export function percent(value, digits = 0) {
  return `${(value * 100).toFixed(digits)}%`;
}

/** Which side of the threshold a sentence (or document) score falls on. */
export function leaning(pAi) {
  if (pAi === null || pAi === undefined) return 'none';
  return pAi >= AI_THRESHOLD ? 'ai' : 'human';
}

/** "14:05" in the user's own locale. */
export function clockTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/** First few words of a text, for tooltips and the history list. */
export function preview(text, max = 60) {
  const flat = text.replace(/\s+/g, ' ').trim();
  return flat.length > max ? `${flat.slice(0, max - 1).trimEnd()}…` : flat;
}
