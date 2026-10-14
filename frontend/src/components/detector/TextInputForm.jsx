/**
 * TextInputForm – the text box, live counters, sample texts and submit button.
 *
 * Validation runs here before anything is sent (usability), but only starts nagging
 * after the first submit attempt, so the user is not told off while still typing.
 * The back end repeats the same checks (security); its message arrives as `serverError`.
 */
import { useState } from 'react';
import { Eraser, ScanSearch, X } from 'lucide-react';

import { MAX_CHARS, MIN_WORDS, countWords, validateText } from '../../config.js';
import { SAMPLES } from './samples.js';

export default function TextInputForm({ text, onTextChange, onSubmit, onCancel, loading, serverError }) {
  const [attempted, setAttempted] = useState(false);

  const words = countWords(text);
  const chars = text.length;
  const localError = attempted ? validateText(text) : null;
  const error = localError ?? serverError;

  function handleSubmit(event) {
    event.preventDefault();
    setAttempted(true);
    if (validateText(text)) return; // message is shown beside the field
    onSubmit(text);
  }

  return (
    <form className="card stack" onSubmit={handleSubmit} noValidate aria-busy={loading}>
      <div className="field">
        <label className="label" htmlFor="text-input">
          Text to check
        </label>
        <p id="text-hint" className="hint">
          Paste at least {MIN_WORDS} words. Longer texts (a few paragraphs) give more reliable results.
        </p>
        <textarea
          id="text-input"
          className="textarea"
          rows={12}
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          disabled={loading}
          aria-invalid={Boolean(error)}
          aria-describedby={`text-hint text-count${error ? ' text-error' : ''}`}
          placeholder="Paste an essay, article or message here…"
          spellCheck={false}
        />
        <div className="field-footer">
          <span id="text-count" className={`counter${chars > MAX_CHARS ? ' counter-over' : ''}`}>
            {words.toLocaleString()} word{words === 1 ? '' : 's'} · {chars.toLocaleString()} /{' '}
            {MAX_CHARS.toLocaleString()} characters
          </span>
        </div>
        {error && (
          <p id="text-error" className="field-error" role="alert">
            {error}
          </p>
        )}
      </div>

      <div className="samples">
        <span className="hint" id="samples-label">
          Try a sample:
        </span>
        <div className="row-wrap" role="group" aria-labelledby="samples-label">
          {SAMPLES.map((sample) => (
            <button
              key={sample.id}
              type="button"
              className="chip"
              onClick={() => onTextChange(sample.text)}
              disabled={loading}
            >
              {sample.label}
            </button>
          ))}
        </div>
      </div>

      <div className="row-wrap form-actions">
        <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
          {loading ? <span className="spinner spinner-sm" aria-hidden="true" /> : <ScanSearch size={18} />}
          {loading ? 'Checking…' : 'Check text'}
        </button>
        {loading ? (
          <button type="button" className="btn" onClick={onCancel}>
            <X size={16} /> Cancel
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              onTextChange('');
              setAttempted(false);
            }}
            disabled={!text}
          >
            <Eraser size={16} /> Clear
          </button>
        )}
      </div>
    </form>
  );
}
