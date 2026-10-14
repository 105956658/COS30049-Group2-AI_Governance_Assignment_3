# TextTrace – front end (React)

React 19 + Vite single-page app for the AI-generated text detector. It sends text to the FastAPI
back end and shows the verdict, its confidence, a per-sentence breakdown, and a comparison of every
check made in the current browser tab.

## Run it

Requires **Node.js 20.19+** (tested on 24.21.0).

```bash
cd frontend
npm ci            # installs the exact versions in package-lock.json
npm run dev       # http://localhost:3000
```

The dev server forwards every `/api/...` request to FastAPI on `http://127.0.0.1:8000`
(see `vite.config.js`), so start the back end first.

### Demo mode (no back end needed)

To work on the UI before the back end exists, create `frontend/.env.local` containing:

```
VITE_USE_MOCK=true
```

Results then come from `src/api/mock.js`, a crude word-pattern heuristic, **not the trained model**.
The header shows a "Demo data" badge while it is on. Including `#error` or `#busy` in the text shows
the 500 and 503 error states. Set it back to `false` (or delete the file) for the real application.

## Pinned dependencies

| Package | Version |
| --- | --- |
| react / react-dom | 19.3.0 |
| react-router-dom | 7.18.4 |
| d3 | 7.9.0 |
| lucide-react | 1.48.0 |
| vite | 8.3.1 |
| @vitejs/plugin-react | 6.1.1 |

Versions are exact in `package.json`, and `.npmrc` sets `save-exact=true` so new installs stay pinned.

## Structure

```
src/
  main.jsx, App.jsx        entry point, routes (/, /about, 404)
  config.js                input limits, threshold, front-end validation
  api/client.js            fetch wrapper: timeouts, offline detection, one error format
  api/detector.js          getHealth(), predict() – switches to mock.js in demo mode
  pages/                   DetectorPage, AboutPage, NotFoundPage
  components/detector/     form, result card, sentence highlights, history table
  components/charts/       SentenceChart, HistoryChart (D3 scales, React-rendered SVG)
  components/common/       ErrorBoundary (fallback page), PageLoader
  hooks/                   session history, back-end status, element size, theme storage
```

## API contract the back end must implement

### `GET /api/health`

```json
{ "status": "ok", "model_loaded": true, "model_version": "rfr-2026-10" }
```

### `POST /api/predict`

Request:

```json
{ "text": "Artificial intelligence has significantly transformed..." }
```

Response `200`:

```json
{
  "label": "ai",
  "confidence": 0.91,
  "ai_score": 0.91,
  "score_range": { "low": 0.72, "high": 1.0 },
  "sentences": [
    { "text": "Artificial intelligence has significantly transformed the landscape.", "p_ai": 0.94 },
    { "text": "Short one.", "p_ai": null }
  ],
  "word_count": 74,
  "model_version": "rfr-2026-10"
}
```

These map directly onto `pipeline.analyze()`: `ai_score` = `overall`, `score_range` = `low`/`high`,
`sentences` as returned (`p_ai: null` = under 4 words, not scored). `label` is `"ai"` when
`ai_score >= 0.5`, and `confidence` is `ai_score` for `"ai"` and `1 - ai_score` for `"human"`.

### Error format (every error, including unexpected ones)

```json
{
  "error": {
    "code": "text_too_short",
    "message": "Text must contain at least 20 words.",
    "details": [{ "field": "text", "message": "Text must contain at least 20 words." }]
  }
}
```

| Status | When | Shown in the UI |
| --- | --- | --- |
| 413 / 422 | text too long (over 10,000 characters), too short (under 20 words), or invalid | beside the text box |
| 429 | rate limit hit | result panel, with Try again |
| 500 | unexpected error (no stack trace in the body) | result panel, with Try again |
| 503 | server busy | result panel, with Try again |

The front end checks the same limits before sending (`src/config.js`) for usability only;
the back end must enforce them itself. If you change a limit, change it in both places.

## Security notes

- User text is only ever rendered as React text children; there is no `dangerouslySetInnerHTML`,
  `window.open` or `window.location` with user input anywhere in `src/`.
- No secrets live in the front end. Every `VITE_*` variable is bundled into public JavaScript, so
  `.env.example` documents only non-secret settings.
- Session history is kept in `sessionStorage`, so it never leaves the browser and is forgotten when
  the tab is closed.
