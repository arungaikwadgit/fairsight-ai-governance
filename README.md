# Fair Sight AI Governance — Prototype

[![Streamlit App](https://img.shields.io/badge/Launch-Streamlit-brightgreen)](https://share.streamlit.io/YOUR_GH_USERNAME/fairsight-ai-governance/main/app.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)


A Streamlit-based prototype to track AI projects, enforce ethical gates, and generate AI-powered recommendations.

## Demo Logins
- **ChiefAIOfficer** → `caios` / `admin123`
- **GovernanceReviewer** → `governance1` / `review123`

## Features
- Clean UI (red/blue/white) + logo
- Simple auth with roles
- 4-gate ethical workflow with required artifacts
- Artifact uploads + gating logic
- **AI Recommendation Model** with policy notes (admin-tunable)
- Local JSON DB (fast hackathon setup) → easy Firestore upgrade
- One-click deploy to Streamlit Cloud

## Quickstart
```bash
pip install -r requirements.txt
streamlit run app.py
```

For full details, see [SETUP.md](SETUP.md) and [DEPLOY.md](DEPLOY.md).

## Deploy on Streamlit Cloud
1. Push this folder to GitHub: `https://github.com/YOUR_GH_USERNAME/fairsight-ai-governance`  
2. Go to Streamlit Cloud and point to `app.py`.  
3. Set Secrets for live AI:
   ```
   OPENAI_API_KEY = sk-...
   OPENAI_MODEL = gpt-4o-mini
   ```
4. (Optional) Add Firebase Admin credentials and update `firestore_db.py`.

## Project Structure
```
fairsight_ai_governance/
├─ app.py                 # Streamlit UI
├─ auth.py                # username/password + roles
├─ firestore_db.py        # local JSON DB (swap to Firestore later)
├─ workflow.py            # gate definitions + validation
├─ ai.py                  # recommendations + policy notes
├─ styles.css             # Tailwind-inspired styling
├─ assets/
│  ├─ logo.svg
│  └─ logo.png
├─ uploads/               # user-uploaded artifacts (runtime)
├─ SETUP.md
├─ DEPLOY.md
├─ requirements.txt
└─ README.md
```

## License
MIT — see [LICENSE](LICENSE).
