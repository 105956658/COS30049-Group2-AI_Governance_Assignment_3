/**
 * DetectorPage – the main workflow: type/paste text → validate → POST /api/predict →
 * show the result, the per-sentence breakdown, and how it compares with earlier checks.
 *
 * Request state is one of 'idle' | 'loading' | 'success' | 'error', so the user can
 * always see what is happening.
 */
import { useEffect, useRef, useState } from 'react';
import { CircleAlert, FileText, RotateCcw, Trash2 } from 'lucide-react';

import TextInputForm from '../components/detector/TextInputForm.jsx';
import ResultCard from '../components/detector/ResultCard.jsx';
import SentenceHighlights from '../components/detector/SentenceHighlights.jsx';
import HistoryTable from '../components/detector/HistoryTable.jsx';
import SentenceChart from '../components/charts/SentenceChart.jsx';
import HistoryChart from '../components/charts/HistoryChart.jsx';
import { predict } from '../api/detector.js';
import useSessionHistory from '../hooks/useSessionHistory.js';
import useDocumentTitle from '../hooks/useDocumentTitle.js';

export default function DetectorPage() {
  useDocumentTitle('Detector');

  const [text, setText] = useState('');
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null); // ApiError from the last request
  const { history, addCheck, clearHistory } = useSessionHistory();
  const [selectedId, setSelectedId] = useState(() => history.at(-1)?.id ?? null);
  const [selectedSentence, setSelectedSentence] = useState(null);

  const controllerRef = useRef(null);
  const resultHeadingRef = useRef(null);
  const focusResult = useRef(false);

  // Cancel an in-flight request if the user leaves the page.
  useEffect(() => () => controllerRef.current?.abort(), []);

  const selectedIndex = history.findIndex((h) => h.id === selectedId);
  const selected = selectedIndex >= 0 ? history[selectedIndex] : null;

  // After a new result arrives, move focus to its heading: screen readers announce it,
  // and on a phone the page scrolls to the result below the form.
  useEffect(() => {
    if (focusResult.current && selected) {
      focusResult.current = false;
      resultHeadingRef.current?.focus();
    }
  }, [selected]);

  async function handleSubmit(value) {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setStatus('loading');
    setError(null);
    try {
      const result = await predict(value, { signal: controller.signal });
      const entry = addCheck(value, result);
      focusResult.current = true;
      setSelectedId(entry.id);
      setSelectedSentence(null);
      setStatus('success');
    } catch (err) {
      if (controller.signal.aborted) return; // cancelled on purpose – not an error
      setError(err);
      setStatus('error');
    }
  }

  function handleCancel() {
    controllerRef.current?.abort();
    setStatus(selected ? 'success' : 'idle');
  }

  function handleTextChange(value) {
    setText(value);
    // An old server message about the previous text no longer applies.
    if (error?.fieldErrors?.text) setError(null);
    if (status === 'error') setStatus(selected ? 'success' : 'idle');
  }

  function selectCheck(id) {
    setSelectedId(id);
    setSelectedSentence(null);
  }

  function handleClear() {
    clearHistory();
    setSelectedId(null);
    setSelectedSentence(null);
    setStatus('idle');
  }

  const loading = status === 'loading';
  // Validation errors (422/413) belong beside the text box; anything else goes in the result panel.
  const fieldError = error?.fieldErrors?.text ?? (error && [413, 422].includes(error.status) ? error.message : null);
  const panelError = status === 'error' && !fieldError ? error : null;

  return (
    <div className="stack-lg">
      <section className="intro">
        <h1>Was this text written by AI?</h1>
        <p className="lead">
          Paste a piece of writing to estimate whether a person or an AI model wrote it, and see which sentences
          drove the result.
        </p>
      </section>

      <div className="detector-grid">
        <TextInputForm
          text={text}
          onTextChange={handleTextChange}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          loading={loading}
          serverError={fieldError}
        />

        <div className="result-panel" aria-live="polite">
          {loading && (
            <div className="card result-loading" role="status">
              <span className="spinner spinner-lg" aria-hidden="true" />
              <p className="m-0">
                <strong>Analysing your text…</strong>
              </p>
              <p className="muted small m-0">Scoring each sentence, then the whole document.</p>
            </div>
          )}

          {!loading && panelError && (
            <div className="card alert alert-danger" role="alert">
              <CircleAlert size={22} aria-hidden="true" />
              <div className="stack-sm">
                <strong>The check could not be completed</strong>
                <span>{panelError.message}</span>
                <div>
                  <button type="button" className="btn btn-sm" onClick={() => handleSubmit(text)}>
                    <RotateCcw size={14} /> Try again
                  </button>
                </div>
              </div>
            </div>
          )}

          {!loading && !panelError && selected && (
            <ResultCard
              entry={selected}
              checkNumber={selectedIndex + 1}
              isLatest={selectedIndex === history.length - 1}
              headingRef={resultHeadingRef}
            />
          )}

          {!loading && !panelError && !selected && (
            <div className="card empty-state">
              <FileText size={40} aria-hidden="true" />
              <p className="m-0">
                <strong>Your result will appear here</strong>
              </p>
              <p className="muted small m-0">Paste some text, or try one of the samples, then press Check text.</p>
            </div>
          )}
        </div>
      </div>

      {selected && (
        <section className="card stack" aria-labelledby="breakdown-heading">
          <div>
            <h2 id="breakdown-heading" className="section-title">
              Sentence breakdown
            </h2>
            <p className="muted m-0">
              The document score combines these sentence scores with writing-style patterns, so a few AI-leaning
              sentences do not automatically make the whole text AI-generated.
            </p>
          </div>
          <SentenceChart
            sentences={selected.result.sentences}
            selected={selectedSentence}
            onSelect={setSelectedSentence}
          />
          <div>
            <h3 className="chart-title">Your text, tinted by sentence</h3>
            <p className="chart-subtitle">
              Orange leans AI, blue leans human; stronger colour means a more confident sentence. Select a sentence
              to find it in the chart.
            </p>
            <SentenceHighlights
              sentences={selected.result.sentences}
              selected={selectedSentence}
              onSelect={setSelectedSentence}
            />
          </div>
        </section>
      )}

      {history.length > 0 && (
        <section className="card stack" aria-labelledby="history-heading">
          <div className="row-between">
            <div>
              <h2 id="history-heading" className="section-title">
                This session
              </h2>
              <p className="muted m-0">
                {history.length} check{history.length === 1 ? '' : 's'}, kept only in this browser tab.
              </p>
            </div>
            <button type="button" className="btn btn-ghost btn-sm" onClick={handleClear} disabled={loading}>
              <Trash2 size={14} /> Clear history
            </button>
          </div>
          <HistoryChart history={history} selectedId={selectedId} onSelect={selectCheck} />
          <HistoryTable history={history} selectedId={selectedId} onSelect={selectCheck} />
        </section>
      )}
    </div>
  );
}
