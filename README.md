# CampusCare — Student Healthcare & Wellness Portal

CampusCare is a learning-oriented full-stack web application for a college health centre. It provides separate student and administrator experiences for appointment requests, basic wellness logging and student document organisation.

## Features

- Student registration, login and logout
- Role-protected student and administrator pages
- Student dashboard and editable profile
- Appointment slot browsing, booking, history and cancellation
- Admin appointment status updates, slot creation and student activation/deactivation
- Daily water, sleep, exercise and mood tracker
- Searchable health-awareness resources
- Private per-student document upload, download and deletion
- SQLite storage, parameterised queries, password hashing and CSRF token checks
- Automated tests with pytest

## Technology

- Python 3
- Flask and Jinja templates
- HTML and CSS
- SQLite
- pytest

## Run locally

Python 3.10 or newer is recommended.

1. Create and activate a virtual environment.
2. Install dependencies with \`pip install -r requirements.txt\`.
3. Copy \`.env.example\` to \`.env\` and set a strong secret key and administrator password.
4. Start the app with \`python app.py\`.
5. Open http://127.0.0.1:5000 in your browser.

On Windows, copy the environment file with \`copy .env.example .env\`. On macOS or Linux, use \`cp .env.example .env\`.

The SQLite database, sample resources and appointment slots are initialized automatically on first run. The demo administrator defaults are only for local evaluation; override ADMIN_EMAIL, ADMIN_PASSWORD and SECRET_KEY in your private .env file before using the application. Never commit .env, database files, uploads or real student/health data.

## Tests

Run \`pytest -q\` after installing the dependencies.

## Project layout

- \`app.py\` — Flask application, routes, authentication, database initialization and file handling
- \`templates/\` — Jinja templates for student and admin pages
- \`static/css/style.css\` — responsive application styles
- \`tests/\` — pytest test suite
- \`database/\` — generated SQLite database (ignored by Git)
- \`uploads/\` — uploaded files (ignored by Git)

## Security and scope

This is an academic prototype, not a production medical-record system. Do not upload real personal or health information. Before deployment, add HTTPS, a production WSGI server, rate limiting, stronger file-content validation, backups, a secure secret-management process and an independent security review. Health resources are educational and are not medical advice.
