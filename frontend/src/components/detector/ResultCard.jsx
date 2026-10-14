/**
 * ResultCard – the verdict. It is the largest element on the page: the label first,
 * then the confidence, then a score bar that shows where the text sits between
 * "human" and "AI", the model's uncertainty range and the decision threshold.
 */
import { Bot, Info, UserRound } from 'lucide-react';

import { AI_THRESHOLD } from '../../config.js';
import { VERDICT, clockTime, percent } from '../../lib/format.js';

// Below this confidence the result sits close to the threshold: say so plainly.
const BORDERLINE = 0.65;

export default function ResultCard({ entry, checkNumber, isLatest, headingRef }) {
  const { result } = entry;
  const { label, confidence, ai_score: score, score_range: range } = result;
  const verdict = VERDICT[label];
  const Icon = label === 'ai' ? Bot : UserRound;
  const scored = result.sentences.filter((s) => s.p_ai !== null).length;
  const rangeLabel = `${percent(range.low)} to ${percent(range.high)}`;

  return (
    <section className={`card result-card result-${label}`} aria-labelledby="result-heading">
      <p className="eyebrow">
        {isLatest ? 'Result' : `Earlier check #${checkNumber} · ${clockTime(entry.checkedAt)}`}
      </p>

      <div className="verdict">
        <span className="verdict-icon" aria-hidden="true">
          <Icon size={32} />
        </span>
        <h2 id="result-heading" ref={headingRef} tabIndex={-1} className="verdict-label">
          {verdict.long}
        </h2>
      </div>

      <p className="confidence">
        <span className="confidence-value">{percent(confidence)}</span>
        <span className="confidence-label">confidence</span>
      </p>

      {/* The score bar: 0 = human, 1 = AI. */}
      <figure className="score-bar-figure">
        <figcaption className="sr-only">
          AI score {percent(score)}. The model's trees ranged from {rangeLabel}. Texts scoring{' '}
          {percent(AI_THRESHOLD)} or more are labelled AI-generated.
        </figcaption>
        <div className="score-bar" aria-hidden="true">
          <div
            className="score-range"
            style={{ left: `${range.low * 100}%`, width: `${(range.high - range.low) * 100}%` }}
          />
          <div className="score-threshold" style={{ left: `${AI_THRESHOLD * 100}%` }} />
          <div className="score-marker" style={{ left: `${score * 100}%` }} />
        </div>
        <div className="score-scale" aria-hidden="true">
          <span>Human-written</span>
          <span>AI score {percent(score)}</span>
          <span>AI-generated</span>
        </div>
      </figure>

      <dl className="result-facts">
        <div>
          <dt>AI score</dt>
          <dd>{percent(score, 1)}</dd>
        </div>
        <div>
          <dt>Model range</dt>
          <dd>{rangeLabel}</dd>
        </div>
        <div>
          <dt>Sentences scored</dt>
          <dd>
            {scored} of {result.sentences.length}
          </dd>
        </div>
        <div>
          <dt>Words</dt>
          <dd>{result.word_count.toLocaleString()}</dd>
        </div>
      </dl>

      {confidence < BORDERLINE && (
        <p className="note note-warning">
          <Info size={16} aria-hidden="true" />
          This text is close to the decision line, so treat the result as uncertain.
        </p>
      )}
      <p className="note">
        <Info size={16} aria-hidden="true" />
        The model range shows how much the model&apos;s 300 decision trees disagree; a wide range means a less
        certain result. This is an estimate, not proof of who wrote the text.
      </p>
    </section>
  );
}
