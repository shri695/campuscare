# MediConnect AI

**An intelligent healthcare management and assistance system using AI and API integration.**

MediConnect AI is a full-stack academic prototype that combines an AI-powered general-health information assistant, doctor discovery, appointment management, patient dashboards, health-record organisation and an administrator workspace.

> **Safety notice:** This is an educational demonstration, not a clinical product. Do not enter real personal or health information. The chatbot does not diagnose, prescribe or replace a qualified healthcare professional. For emergencies in India, call 112 or visit an emergency department.

## Features implemented

- Patient registration and login with hashed passwords, consent capture and JWT authentication.
- Role-protected patient and administrator endpoints.
- AI chatbot integration using the Gemini `generateContent` REST API. The API key remains on the Flask server.
- Emergency phrase pre-check that immediately displays an urgent-care warning instead of asking the AI to assess an emergency.
- Per-user chat history stored by the backend.
- Doctor directory with text and specialization filters; starter doctor data is fictional.
- Appointment booking, history and cancellation. A database unique index prevents duplicate active bookings for a doctor/time slot.
- Patient dashboard and editable basic profile.
- Health-record creation, update, viewing and deletion, with owner-scoped access.
- Nearby hospital search through Google Maps Platform when configured; otherwise the app provides a Google Maps search link.
- Admin overview, patient list, appointment cancellation and doctor creation.
- Resend email confirmation integration for appointments (optional).
- Responsive React interface and a Flask API; MongoDB Atlas is supported, with SQLite as a zero-setup local/CI demo store.

## Technology stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React, Vite, React Router, Lucide | Responsive single-page user interface |
| Backend | Python, Flask, Flask-CORS | REST API, validation, security and application rules |
| Database | MongoDB Atlas / SQLite demo fallback | Users, doctors, appointments, health records and chat history |
| AI | Gemini API (`generateContent`) | General health-information chatbot |
| Authentication | JWT, Werkzeug password hashing | Signed access tokens and password protection |
| External APIs | Google Maps Places API, Resend | Nearby hospitals and appointment emails |
| Testing | pytest, GitHub Actions | Backend route and security checks |

## Run locally

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Windows: copy .env.example .env
# macOS/Linux: cp .env.example .env
python app.py
```

The backend runs at `http://127.0.0.1:5000`. Without `MONGODB_URI`, it creates a local SQLite database under `backend/instance/` and inserts fictional starter doctors. To use MongoDB Atlas, set `MONGODB_URI` and `MONGODB_DATABASE` in `backend/.env`.

### 2. Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### 3. Enable the AI assistant

Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/app/apikey). Add it to `backend/.env` as `GEMINI_API_KEY=...`, then restart Flask. The default model is configured through `GEMINI_MODEL` (currently `gemini-3.8-flash`). The browser never receives this secret. Without a key, the chat endpoint returns a clear configuration message instead of pretending to generate an AI response.

### 4. Optional integrations

- **Google Maps:** set `MAPS_API_KEY` with the Places API enabled. Without it, the app returns a Google Maps search link.
- **Email:** set `RESEND_API_KEY` and a verified `EMAIL_FROM` sender. Appointment booking still works when email is not configured; the UI/API reports that no email was sent.

## Demo administrator

The local demo creates an administrator account from `ADMIN_EMAIL` and `ADMIN_PASSWORD`. The example values are placeholders for local evaluation only. Change them before running the app and never deploy the example credentials.

## Tests

```bash
cd backend
pytest -q
```

GitHub Actions runs the backend tests on pushes and pull requests to the `mediconnect-ai` branch.

## API overview

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | Public | Create a patient account and record consent |
| POST | `/api/auth/login` | Public | Authenticate and issue a JWT |
| GET | `/api/auth/me` | Authenticated | Return current account |
| GET / PUT | `/api/profile` | Authenticated | Read/update basic profile |
| POST / GET | `/api/chat` / `/api/chat/history` | Patient | Ask the AI assistant / view own history |
| GET | `/api/doctors` | Public | Search doctors |
| GET | `/api/doctors/{id}` | Public | View doctor details |
| GET | `/api/hospitals/nearby` | Patient | Search nearby hospitals |
| POST / GET | `/api/appointments` | Patient | Book/list own appointments |
| POST | `/api/appointments/{id}/cancel` | Patient | Cancel own appointment |
| GET / POST | `/api/health-records` | Patient | List/create own records |
| PUT / DELETE | `/api/health-records/{id}` | Patient | Update/delete own records |
| GET | `/api/dashboard` | Patient | Patient dashboard summary |
| GET | `/api/admin/stats` | Admin | Overview, bookings and patients |
| POST / PUT | `/api/admin/doctors` | Admin | Create/update doctor listing |
| PATCH | `/api/admin/appointments/{id}` | Admin | Cancel an appointment |

Protected API requests use `Authorization: Bearer <token>`. API errors use a JSON object with an `error` field and suitable HTTP status code.

## Security and privacy notes

- Passwords are salted hashes; raw passwords are never stored.
- JWTs are short-lived; every protected route verifies the token and role.
- Health records and chat history are queried by the authenticated user's ID.
- AI and Maps keys are read by the backend from environment variables and are not embedded in React.
- The chat prompt limits the assistant to general information; emergency phrases are handled before the AI call, and a disclaimer is added by the backend.
- Use HTTPS, strong secrets, a restricted CORS origin, rate limiting, backups, database access controls and a security/legal review before any real deployment.

## Project structure

```text
MediConnect-AI/
├── backend/
│   ├── app.py
│   ├── store.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── main.jsx
│       └── styles.css
├── .github/workflows/tests.yml
├── .gitignore
└── README.md
```

## References

- Flask: https://flask.palletsprojects.com/
- React: https://react.dev/
- MongoDB: https://www.mongodb.com/docs/
- PyMongo: https://pymongo.readthedocs.io/
- Gemini API: https://ai.google.dev/gemini-api/docs
- Google Maps Places API: https://developers.google.com/maps/documentation/places/web-service
- JSON Web Token (RFC 7519): https://datatracker.ietf.org/doc/html/rfc7519
- OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/
