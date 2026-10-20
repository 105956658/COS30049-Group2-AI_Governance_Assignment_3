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

# Innovation Security Defenses

- Unsafe File Upload


- Denial of Service


# Advanced Security
- Detection Evasion
