/**
 * SentenceHighlights – the submitted text, each sentence tinted by its AI probability.
 *
 * SECURITY: every sentence is rendered as a normal React text child, which React escapes.
 * Never switch this to dangerouslySetInnerHTML to "make highlighting easier": the text is
 * user input, so that would let a pasted <img onerror=…> run script in the page.
 */
import { leaning, percent } from '../../lib/format.js';

/** Tint strength grows with distance from 0.5, so near-threshold sentences stay pale. */
function tint(pAi) {
  const side = leaning(pAi);
  if (side === 'none') return undefined;
  const strength = Math.round(Math.abs(pAi - 0.5) * 2 * 45) + 8; // 8%–53%
  return { backgroundColor: `color-mix(in srgb, var(--${side}) ${strength}%, transparent)` };
}

export default function SentenceHighlights({ sentences, selected, onSelect }) {
  return (
    <div className="highlights" aria-label="Submitted text with each sentence tinted by AI probability">
      {sentences.map((sentence, i) => {
        const side = leaning(sentence.p_ai);
        const description =
          side === 'none' ? 'too short to score' : `${percent(sentence.p_ai)} likely AI-generated`;
        return (
          <span key={i}>
            <button
              type="button"
              className={`sentence sentence-${side}${selected === i ? ' is-selected' : ''}`}
              style={tint(sentence.p_ai)}
              aria-pressed={selected === i}
              aria-label={`Sentence ${i + 1}, ${description}: ${sentence.text}`}
              title={`Sentence ${i + 1}: ${description}`}
              onClick={() => onSelect(selected === i ? null : i)}
            >
              {sentence.text}
            </button>{' '}
          </span>
        );
      })}
    </div>
  );
}
