# COS30049-Group2-AI_Governance
Group project for COS30049 Computing Technology Innovation Project

# Environment Setup (Requires Miniconda or Anaconda)

1. Create the environment with the exact versions used in the report

>> conda create -n ai-detect python=3.13 -y

>> conda activate ai-detect

2. Core libraries

>> conda install -c conda-forge pandas=3.0.6 numpy=2.5.3 scikit-learn=1.9.1 lightgbm=4.7.0 joblib=1.6.0 -y

3. Plotting + notebook (EDA only)

>> conda install -c conda-forge matplotlib seaborn jupyter -y

# Data
The data folder is gitignored because the raw CSVs are too large for GitHub (one exceeds the 100MB hard limit). Download the datasets yourself and place them in the data folder before running the file:

1. DAIGT V2 Train Dataset: https://www.kaggle.com/datasets/thedrcat/daigt-v2-train-dataset
2. AI vs Human Text Classification Dataset 2026: https://www.kaggle.com/datasets/alitaqishah/ai-vs-human-text-classification-dataset-2026
3. AI Vs Human Text: https://www.kaggle.com/datasets/shanegerami/ai-vs-human-text


# Data processing
Run the notebook top to botton:

>> jupyter notebook eda.ipynb

# Train the models
Run in this order – each step uses the outputs of the previous one. All scripts use fixed random seeds.

Baseline sentence classifiers
>> python classifier.py --model logreg     # -> models/clf_logreg.joblib

>> python classifier.py --model svc        # -> models/clf_svc.joblib

Final sentence classifier: LightGBM
(early stopping uses 5,000 documents held back from the training split)

>> python lgbm_classifier.py               # -> models/classifier.joblib

GMM clustering on AI training sentences only (k = 6, full covariance)
(also saves the BIC curve and cluster profile tables)

>>python gmm.py --k 6                     # -> models/gmm.joblib            

Document-level regressor, fitted on the VALIDATION split
(documents the classifier and GMM never saw), then evaluated on test + holdout_2026

>>python regressor.py                     # -> models/regressor.joblib

# Make Predictions
Predict a single text:

>> python pipeline.py --text "Paste the text you want to check here."          

# Reference
Used for feature engineering

1. https://academic.oup.com/dsh/advance-article/doi/10.1093/llc/fqag064/8714041
2. https://arxiv.org/abs/2303.03697
3. https://www.researchgate.net/publication/398588043_Feature-Based_Detection_of_AI-Generated_Text_An_Analysis_of_Stylometric_and_Perplexity_Markers_in_Contemporary_Large_Language_Models

# Front End (React)
The web interface is in the frontend folder. It is built with React 19 and Vite, and talks to the FastAPI back end through the /api path. More detail (folder structure, API contract, error format) is in frontend/README.md.

1. Install Node.js 20.19 or newer, then check the version (tested on Node 24.21.0)

>> node -v

2. Install the front-end packages (exact versions from package-lock.json; first time only)

>> cd frontend

>> npm ci

3. Start the development server, then open http://localhost:3000 in a browser

>> npm run dev

Press Ctrl + C in the terminal to stop it. The server must run on port 3000; if that port is already in use, it stops with an error instead of switching ports.

### Connecting to the back end
In development, every request to /api is forwarded to the FastAPI server at http://127.0.0.1:8000, so start the back end first. The header shows "Model online" when the back end is reachable and "Service offline" when it is not.

### Demo mode (front end only, no back end)
To work on the interface without the back end, create a file named .env.local inside the frontend folder containing:

>> VITE_USE_MOCK=true

Then restart npm run dev. A "Demo data" badge appears in the header, and results come from a simple word-pattern heuristic in src/api/mock.js, not the trained model. Delete .env.local (or set the value to false) and restart to use the real model.

File uploads always use the real backend, including in demo mode.
Start FastAPI to test file uploads.

### Pinned front-end versions
| Package | Version |
| --- | --- |
| react / react-dom | 19.3.0 |
| react-router-dom | 7.18.4 |
| d3 | 7.9.0 |
| lucide-react | 1.48.0 |
| vite | 8.3.1 |
| @vitejs/plugin-react | 6.1.1 |

# Threat Model

1. Who would want to attack your application?

- Students

2. What are they trying to achieve?

- Students trying to pass AI-generated work and claim it as their own

3. What can they actually do to it?

- Students sometimes overlook that they include sensitive information (names, contacts, etc.)

# Security Hygiene

- **Safe text rendering:** Submitted sentences are rendered as React text
  children rather than interpreted as HTML.
- **Backend input limits:** Text is limited to 10,000 characters by default.
  Uploaded files are limited to 32,000 bytes, and the total request body
  is limited to 41,024 bytes by default. Backend checks enforce these limits
  independently of frontend validation.
- **Restricted CORS:** The default allowed origins are
  http://localhost:3000 and http://127.0.0.1:3000.
  Deployment origins can be configured using ALLOWED_ORIGINS.
  CORS controls browser access; it is not authentication.
- **Secret handling:** Local environment files and private-key file patterns
  are excluded by .gitignore. VITE_* variables are public build settings
  and must never contain secrets. Gitleaks scans of local files and Git
  history reported no secrets detected within their scan scope.

CORS preflight tests returned HTTP 200 for http://localhost:3000
and HTTP 400 with "Disallowed CORS origin" for https://example.com.


# Innovation Security Defenses

## Unsafe File Upload 

### Threat and defence

An attacker can bypass browser validation and send oversized files,
crafted filenames, or binary content disguised as plain text directly
to POST /api/predict-file.

The backend validates uploads in backend/upload_security.py before
model inference:

- Allows only filenames ending in .txt (case-insensitive).
- Rejects filenames containing /, \, or ASCII control characters below 32.
- Reads at most 32,001 bytes and rejects files larger than 32,000 bytes.
- Decodes actual content as UTF-8, with optional BOM support.
- Rejects unsupported control characters, empty files, and whitespace-only content.
- Enforces the character limit and reuses prediction validation,
  including the minimum word count.
- Closes uploaded files in a finally block. Application code does not
  save uploads to user-supplied paths or execute them. Multipart handling
  may use temporary storage.

Frontend checks provide early feedback, but the backend independently
enforces validation. The declared MIME type is not trusted as proof
of valid content.

### Direct API test results

The following tests were performed with curl.exe against our own
application at http://127.0.0.1:8000 on 27 October 2026,
bypassing frontend validation.

| Test | Submitted input | Observed response |
| --- | --- | --- |
| Oversized file | 32,001 ASCII bytes in large.txt | HTTP 413: file_too_large |
| Crafted filename | Plain text sent with filename=../test.txt | HTTP 415: unsupported_file_type |
| Disguised binary content | Bytes 0, 1, 2, 3 in fake.txt, declared as text/plain | HTTP 415: invalid_file_content |

All three tested requests were rejected by backend upload validation
before model inference. Response screenshots were captured.

### Trade-offs and limitations

Only UTF-8 plain-text uploads are supported. PDF, Word documents,
other encodings, and files above the limits must be converted or
shortened first.

Encoding and control-character validation is not an antivirus scan.
HTML-like content that is valid plain text may be accepted, but
submitted text is displayed through React text children rather than
interpreted as HTML.

Validation adds a bounded read and content scan before inference,
in exchange for restricting supported file formats and sizes.

### Video demonstration status

The protected application has passed the three direct API tests above.
A comparison against a local unprotected version remains to be recorded
for the video, together with an explanation of the defence and its costs.


- Denial of Service


# Advanced Security
- Detection Evasion
