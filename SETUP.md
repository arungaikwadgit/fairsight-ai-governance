# SETUP.md — Local Development

## 1) Prereqs
- Python 3.10+
- `pip`

## 2) Create virtual env & install
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3) Environment
- (Optional) Set OpenAI key for live recommendations:
```bash
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o-mini
```
Without the key, the app uses a safe offline fallback.

## 4) Run
```bash
streamlit run app.py
```

## 5) Default logins
- `caios` / `admin123` (Chief AI Officer)
- `governance1` / `review123` (Governance Reviewer)

## 6) Data storage
- Prototype uses `local_db.json`. Uploaded files go under `uploads/`.
- To move to Firestore later, replace `firestore_db.py` methods with Firebase Admin SDK calls.
