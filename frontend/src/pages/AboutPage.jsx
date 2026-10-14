/**
 * AboutPage – who the tool is for, how the model reaches a verdict, and its limits.
 * The numbers come from results/regressor_results.csv and
 * evaluation_final/metrics_comparison.csv (Assignment 2 evaluation).
 */
import { Link } from 'react-router-dom';
import { Layers, ListTree, ScanText, ShieldAlert, TreeDeciduous } from 'lucide-react';
import useDocumentTitle from '../hooks/useDocumentTitle.js';

const STEPS = [
  {
    icon: ScanText,
    title: '1. Split into sentences',
    body: 'The text is split into sentences. Sentences under four words carry too little signal and are not scored; they appear grey in the breakdown.',
  },
  {
    icon: ListTree,
    title: '2. Score each sentence',
    body: 'A LightGBM classifier reads style features of each sentence – length, word length, vocabulary variety, punctuation – and estimates the probability that it was AI-generated.',
  },
  {
    icon: Layers,
    title: '3. Group writing styles',
    body: 'A Gaussian mixture model places each sentence among six writing-style clusters learned from AI text, capturing patterns a single probability misses.',
  },
  {
    icon: TreeDeciduous,
    title: '4. Judge the whole document',
    body: 'A random forest of 300 trees combines the sentence scores and style clusters into one AI score. The spread of the trees’ answers is shown as the model range.',
  },
];

export default function AboutPage() {
  useDocumentTitle('How it works');

  return (
    <div className="stack-lg prose-page">
      <section className="intro">
        <p className="eyebrow">How it works</p>
        <h1>From your text to a verdict</h1>
        <p className="lead">
          TextTrace is for teachers, editors and moderators who need a quick second opinion on whether a piece of
          writing was produced by an AI model. It gives an estimate with its uncertainty, and shows which sentences
          drove it, so a person can make the final call.
        </p>
      </section>

      <ol className="steps">
        {STEPS.map(({ icon: Icon, title, body }) => (
          <li key={title} className="card step">
            <Icon size={24} className="step-icon" aria-hidden="true" />
            <h2 className="step-title">{title}</h2>
            <p className="muted m-0">{body}</p>
          </li>
        ))}
      </ol>

      <section className="card stack-sm" aria-labelledby="reading-heading">
        <h2 id="reading-heading" className="section-title">
          Reading a result
        </h2>
        <dl className="definitions">
          <dt>Verdict</dt>
          <dd>
            Texts with an AI score of 50% or more are labelled <em>Likely AI-generated</em>, the rest{' '}
            <em>Likely human-written</em>.
          </dd>
          <dt>Confidence</dt>
          <dd>How far the score is on the side of the verdict: an AI score of 90% is 90% confidence in “AI”, a score of 20% is 80% confidence in “human”.</dd>
          <dt>Model range</dt>
          <dd>
            The 5th to 95th percentile of the 300 trees’ individual answers. It measures disagreement inside the
            model, not a guaranteed 90% interval.
          </dd>
        </dl>
      </section>

      <section className="card stack-sm callout-warning" aria-labelledby="limits-heading">
        <h2 id="limits-heading" className="section-title row">
          <ShieldAlert size={22} aria-hidden="true" /> Limitations – please read
        </h2>
        <ul className="m-0">
          <li>
            On the test set drawn from the training sources, the model scored 93.6% accuracy (ROC AUC 0.98).
          </li>
          <li>
            On a newer 2026 dataset it did much worse: 53.7% accuracy, and it labelled{' '}
            <strong>77% of human-written texts as AI-generated</strong>. Writing from newer AI models, and short
            texts, are the weakest cases.
          </li>
          <li>
            A result is therefore never proof. Do not use it on its own to accuse anyone of using AI.
          </li>
          <li>
            Your text is sent to the server only to be scored. This page keeps the history of your checks in this
            browser tab only, and forgets it when the tab is closed.
          </li>
        </ul>
      </section>

      <div>
        <Link to="/" className="btn btn-primary">
          Try the detector
        </Link>
      </div>
    </div>
  );
}
