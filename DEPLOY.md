# DEPLOY.md — Streamlit Community Cloud

## 1) Push to GitHub
- Commit this project to a public repo (you can make it private on paid plans).

## 2) Create Streamlit app
- Go to https://share.streamlit.io
- "Deploy an app" → Connect your repo → pick `app.py` as the entrypoint.
- Add **secrets** if using live AI:
  - `OPENAI_API_KEY: <your key>`
  - `OPENAI_MODEL: gpt-4o-mini`

## 3) Autodeploy
- Streamlit Cloud will auto-redeploy on pushes to the chosen branch.

## 4) Firebase (optional)
For a real Firestore backend on Streamlit Cloud:
- Add a service account JSON to Streamlit **Secrets**.
- Use Firebase Admin SDK in `firestore_db.py` to read/write projects and artifacts (you can also use GCS for files).
- Because Streamlit runs server-side, Firestore Security Rules don’t apply; implement role checks in code.
