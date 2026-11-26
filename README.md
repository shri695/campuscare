# MediConnect AI
**AI-enabled healthcare management and assistance — academic full-stack project**

MediConnect AI brings together an AI-powered general-health information assistant, doctor discovery, appointment management, personal health records and a patient/admin dashboard.

## Included in this repository
The application source is published in **`mediconnect-ai/`** after the first CI build. It contains the React + Vite frontend, Flask REST API, SQLite demo store, MongoDB Atlas adapter, environment template and pytest suite.

## Run locally
1. Backend: `cd mediconnect-ai/backend`, create/activate a Python virtual environment, run `pip install -r requirements.txt`, copy `.env.example` to `.env`, then run `python app.py`.
2. Frontend: `cd mediconnect-ai/frontend`, run `npm install` and `npm run dev`.
3. Open `http://localhost:5173`. The API defaults to `http://127.0.0.1:5000`.

SQLite demo storage works without a cloud database. Set `MONGODB_URI` and `MONGODB_DATABASE` to use MongoDB Atlas. Set `GEMINI_API_KEY` in the backend environment to enable live AI responses. Google Maps and Resend integrations are optional and require server-side keys.

## AI safety
The chatbot provides general educational information only. It is not for diagnosis, prescriptions or dosage advice. Emergency phrase checks display an urgent-care warning before any AI request. Do not enter real personal or health information into this academic prototype.

## Verification
GitHub Actions reconstructs the source bundle, runs backend pytest tests, builds the frontend, and then publishes the extracted application directory on the `mediconnect-ai` branch.

