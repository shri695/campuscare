import os, sqlite3, secrets
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')
DB_PATH = os.getenv('DATABASE_PATH', str(BASE / 'database' / 'campuscare.db'))
UPLOAD_DIR = BASE / 'uploads'
ALLOWED = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev-only-change-this-key'),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)
UPLOAD_DIR.mkdir(exist_ok=True)
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY, full_name TEXT NOT NULL,
 email TEXT NOT NULL COLLATE NOCASE UNIQUE, password_hash TEXT NOT NULL,
 role TEXT NOT NULL DEFAULT 'student' CHECK(role IN ('student','admin')),
 is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS profiles(
 id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 college TEXT DEFAULT '', course TEXT DEFAULT '', semester INTEGER,
 phone TEXT DEFAULT '', address TEXT DEFAULT '', emergency_contact TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS slots(
 id INTEGER PRIMARY KEY, slot_date TEXT NOT NULL, start_time TEXT NOT NULL,
 end_time TEXT NOT NULL, provider TEXT NOT NULL DEFAULT 'Campus Health Centre',
 is_active INTEGER DEFAULT 1, UNIQUE(slot_date,start_time,provider)
);
CREATE TABLE IF NOT EXISTS appointments(
 id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES users(id),
 slot_id INTEGER NOT NULL REFERENCES slots(id), reason TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending'
 CHECK(status IN ('pending','confirmed','completed','cancelled','rejected')),
 admin_notes TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_slot ON appointments(slot_id)
 WHERE status IN ('pending','confirmed','completed');
CREATE TABLE IF NOT EXISTS wellness(
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 record_date TEXT NOT NULL, water_ml INTEGER DEFAULT 0, sleep_hours REAL DEFAULT 0,
 exercise_minutes INTEGER DEFAULT 0, mood TEXT DEFAULT 'Okay', notes TEXT DEFAULT '',
 UNIQUE(user_id,record_date)
);
CREATE TABLE IF NOT EXISTS resources(
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL,
 summary TEXT NOT NULL, content TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents(
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 original_name TEXT NOT NULL, stored_name TEXT NOT NULL UNIQUE,
 uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
);
'''

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(_=None):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    if not conn.execute('SELECT 1 FROM users WHERE role="admin"').fetchone():
        conn.execute(
            'INSERT INTO users(full_name,email,password_hash,role) VALUES(?,?,?,?)',
            ('CampusCare Admin', os.getenv('ADMIN_EMAIL','admin@campuscare.local'),
             generate_password_hash(os.getenv('ADMIN_PASSWORD','Admin@12345')), 'admin')
        )
    if not conn.execute('SELECT 1 FROM resources LIMIT 1').fetchone():
        rows = [
            ('Basic First Aid','first_aid','Simple steps for common minor injuries.','Clean minor cuts, apply gentle pressure and seek professional care for deep wounds or heavy bleeding.'),
            ('Healthy Eating on Campus','nutrition','Practical balanced-meal habits.','Choose a mix of vegetables, fruit, protein and whole grains. Stay hydrated and avoid skipping meals.'),
            ('Managing Academic Stress','mental_wellness','Small habits that support wellbeing.','Break tasks into manageable steps, take short breaks and reach out to trusted people when stress feels difficult.'),
            ('Building a Sleep Routine','sleep','Improve consistency in your sleep schedule.','Keep a regular sleep and wake time, reduce late caffeine and create a quiet wind-down routine.'),
            ('Staying Active','fitness','Add movement to a busy student day.','Try short walks, stretching or other activities you enjoy. Increase activity gradually.'),
            ('Preventive Health','preventive_care','Make routine health checks part of self-care.','Use campus health services for appropriate check-ups and consult qualified professionals about concerns.')
        ]
        conn.executemany('INSERT INTO resources(title,category,summary,content) VALUES(?,?,?,?)', rows)
    if not conn.execute('SELECT 1 FROM slots LIMIT 1').fetchone():
        for offset in range(1, 15):
            day = (date.today() + timedelta(days=offset)).isoformat()
            for start in ['09:30','10:30','11:30','14:00','15:00']:
                hour, minute = map(int, start.split(':'))
                end = f'{hour + 1:02d}:{minute:02d}'
                conn.execute(
                    'INSERT OR IGNORE INTO slots(slot_date,start_time,end_time,provider) VALUES(?,?,?,?)',
                    (day, start, end, 'Campus Health Centre')
                )
    conn.commit()
    conn.close()

@app.before_request
def csrf_prepare():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(24)
    if request.method in {'POST','PUT','PATCH','DELETE'}:
        token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not token or not secrets.compare_digest(token, session.get('csrf','')):
            abort(403)

def get_user():
    uid = session.get('user_id')
    return db().execute(
        'SELECT * FROM users WHERE id=? AND is_active=1', (uid,)
    ).fetchone() if uid else None

@app.context_processor
def inject_globals():
    return {'csrf_token': session.get('csrf',''), 'current_user': get_user()}

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not get_user():
            flash('Please log in to continue.','warning')
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapped

def role_required(role):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = get_user()
            if not user:
                return redirect(url_for('login'))
            if user['role'] != role:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return deco

def page(name, **kwargs):
    return render_template(name, **kwargs)

def allowed_file_signature(filename, data):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    signatures = {
        'pdf': data.startswith(b'%PDF-'),
        'png': data.startswith(b'\x89PNG\r\n\x1a\n'),
        'jpg': data.startswith(b'\xff\xd8\xff'),
        'jpeg': data.startswith(b'\xff\xd8\xff'),
        'doc': data.startswith(bytes.fromhex('D0CF11E0A1B11AE1')),
        'docx': data.startswith(b'PK\x03\x04')
    }
    return signatures.get(ext, False)

@app.route('/')
def home():
    return redirect(url_for('dashboard') if get_user() else url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('full_name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        if len(name) < 2 or '@' not in email or len(password) < 8:
            flash('Enter a valid name and email. Password must contain at least 8 characters.','danger')
        else:
            try:
                cur = db().execute(
                    'INSERT INTO users(full_name,email,password_hash) VALUES(?,?,?)',
                    (name,email,generate_password_hash(password))
                )
                db().execute('INSERT INTO profiles(user_id) VALUES(?)', (cur.lastrowid,))
                db().commit()
                flash('Account created. Please log in.','success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('An account with that email already exists.','danger')
    return page('auth.html', mode='register')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = db().execute(
            'SELECT * FROM users WHERE email=?',
            (request.form.get('email','').strip(),)
        ).fetchone()
        if user and user['is_active'] and check_password_hash(user['password_hash'], request.form.get('password','')):
            session.clear()
            session['user_id'] = user['id']
            session['csrf'] = secrets.token_urlsafe(24)
            return redirect(url_for('admin') if user['role'] == 'admin' else url_for('dashboard'))
        flash('Invalid email or password.','danger')
    return page('auth.html', mode='login')

@app.post('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_user()
    if user['role'] == 'admin':
        return redirect(url_for('admin'))
    appointments = db().execute(
        'SELECT a.*,s.slot_date,s.start_time,s.provider FROM appointments a '
        'JOIN slots s ON s.id=a.slot_id WHERE a.student_id=? '
        'ORDER BY s.slot_date DESC,s.start_time DESC', (user['id'],)
    ).fetchall()
    today = db().execute(
        'SELECT * FROM wellness WHERE user_id=? AND record_date=?',
        (user['id'], date.today().isoformat())
    ).fetchone()
    docs = db().execute(
        'SELECT COUNT(*) n FROM documents WHERE user_id=?', (user['id'],)
    ).fetchone()['n']
    return page('dashboard.html', appointments=appointments, wellness=today, docs=docs)

@app.route('/profile', methods=['GET','POST'])
@login_required
@role_required('student')
def profile():
    user = get_user()
    profile_row = db().execute('SELECT * FROM profiles WHERE user_id=?', (user['id'],)).fetchone()
    if request.method == 'POST':
        db().execute(
            'UPDATE users SET full_name=? WHERE id=?',
            (request.form.get('full_name',user['full_name']).strip(), user['id'])
        )
        db().execute(
            'UPDATE profiles SET college=?,course=?,semester=?,phone=?,address=?,emergency_contact=? WHERE user_id=?',
            (request.form.get('college',''), request.form.get('course',''),
             request.form.get('semester') or None, request.form.get('phone',''),
             request.form.get('address',''), request.form.get('emergency_contact',''), user['id'])
        )
        db().commit()
        flash('Profile updated.','success')
        return redirect(url_for('profile'))
    return page('profile.html', profile=profile_row)

@app.route('/appointments', methods=['GET','POST'])
@login_required
@role_required('student')
def appointments():
    user = get_user()
    if request.method == 'POST':
        slot_id = request.form.get('slot_id')
        reason = request.form.get('reason','').strip()
        if len(reason) < 5 or len(reason) > 500:
            flash('Reason must be 5–500 characters.','danger')
        else:
            try:
                slot = db().execute(
                    'SELECT * FROM slots WHERE id=? AND is_active=1 AND slot_date>=?',
                    (slot_id, date.today().isoformat())
                ).fetchone()
                if not slot:
                    flash('That slot is no longer available.','danger')
                else:
                    db().execute(
                        'INSERT INTO appointments(student_id,slot_id,reason) VALUES(?,?,?)',
                        (user['id'],slot_id,reason)
                    )
                    db().commit()
                    flash('Appointment requested.','success')
            except sqlite3.IntegrityError:
                db().rollback()
                flash('Sorry, this slot has already been booked.','danger')
        return redirect(url_for('appointments'))
    slots = db().execute(
        "SELECT s.* FROM slots s WHERE s.is_active=1 AND s.slot_date>=? "
        "AND NOT EXISTS(SELECT 1 FROM appointments a WHERE a.slot_id=s.id "
        "AND a.status IN ('pending','confirmed','completed')) ORDER BY s.slot_date,s.start_time",
        (date.today().isoformat(),)
    ).fetchall()
    history = db().execute(
        'SELECT a.*,s.slot_date,s.start_time,s.provider FROM appointments a '
        'JOIN slots s ON s.id=a.slot_id WHERE a.student_id=? ORDER BY a.created_at DESC',
        (user['id'],)
    ).fetchall()
    return page('appointments.html', slots=slots, history=history)

@app.post('/appointments/<int:aid>/cancel')
@login_required
@role_required('student')
def cancel_appointment(aid):
    cur = db().execute(
        "UPDATE appointments SET status='cancelled' WHERE id=? AND student_id=? "
        "AND status IN ('pending','confirmed')", (aid,get_user()['id'])
    )
    db().commit()
    flash('Appointment cancelled.' if cur.rowcount else 'Appointment cannot be cancelled.',
          'success' if cur.rowcount else 'warning')
    return redirect(url_for('appointments'))

@app.route('/wellness', methods=['GET','POST'])
@login_required
@role_required('student')
def wellness():
    uid = get_user()['id']
    if request.method == 'POST':
        try:
            values = (
                uid, request.form.get('record_date') or date.today().isoformat(),
                int(request.form.get('water_ml',0)), float(request.form.get('sleep_hours',0)),
                int(request.form.get('exercise_minutes',0)), request.form.get('mood','Okay'),
                request.form.get('notes','')[:500]
            )
            if not 0 <= values[2] <= 10000 or not 0 <= values[3] <= 24 or not 0 <= values[4] <= 1440:
                raise ValueError()
            db().execute(
                'INSERT INTO wellness(user_id,record_date,water_ml,sleep_hours,exercise_minutes,mood,notes) '
                'VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,record_date) DO UPDATE SET '
                'water_ml=excluded.water_ml,sleep_hours=excluded.sleep_hours,'
                'exercise_minutes=excluded.exercise_minutes,mood=excluded.mood,notes=excluded.notes',
                values
            )
            db().commit()
            flash('Wellness record saved.','success')
        except (ValueError, sqlite3.IntegrityError):
            flash('Please enter valid wellness values.','danger')
        return redirect(url_for('wellness'))
    records = db().execute(
        'SELECT * FROM wellness WHERE user_id=? ORDER BY record_date DESC LIMIT 30', (uid,)
    ).fetchall()
    return page('wellness.html', records=records)

@app.route('/resources')
@login_required
def resources():
    query = request.args.get('q','').strip()
    category = request.args.get('category','')
    sql = 'SELECT * FROM resources WHERE 1=1'
    args = []
    if query:
        sql += ' AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)'
        args += [f'%{query}%'] * 3
    if category:
        sql += ' AND category=?'
        args.append(category)
    rows = db().execute(sql + ' ORDER BY category,title', args).fetchall()
    return page('resources.html', resources=rows, q=query, category=category)

@app.route('/documents', methods=['GET','POST'])
@login_required
@role_required('student')
def documents():
    uid = get_user()['id']
    if request.method == 'POST':
        uploaded = request.files.get('document')
        if not uploaded or not uploaded.filename or '.' not in uploaded.filename:
            flash('Choose a file to upload.','danger')
        else:
            ext = uploaded.filename.rsplit('.',1)[1].lower()
            if ext not in ALLOWED:
                flash('Allowed: PDF, PNG, JPG, DOC and DOCX.','danger')
            else:
                data = uploaded.read()
                if not data or not allowed_file_signature(uploaded.filename, data):
                    flash('The file content does not match its extension.','danger')
                else:
                    stored = secrets.token_hex(16) + '.' + ext
                    (UPLOAD_DIR / stored).write_bytes(data)
                    db().execute(
                        'INSERT INTO documents(user_id,original_name,stored_name) VALUES(?,?,?)',
                        (uid, secure_filename(uploaded.filename), stored)
                    )
                    db().commit()
                    flash('Document uploaded.','success')
        return redirect(url_for('documents'))
    rows = db().execute(
        'SELECT * FROM documents WHERE user_id=? ORDER BY uploaded_at DESC', (uid,)
    ).fetchall()
    return page('documents.html', documents=rows)

@app.get('/documents/<int:doc_id>/download')
@login_required
@role_required('student')
def download_document(doc_id):
    doc = db().execute(
        'SELECT * FROM documents WHERE id=? AND user_id=?', (doc_id,get_user()['id'])
    ).fetchone()
    if not doc:
        abort(404)
    return send_from_directory(
        UPLOAD_DIR, doc['stored_name'], as_attachment=True, download_name=doc['original_name']
    )

@app.post('/documents/<int:doc_id>/delete')
@login_required
@role_required('student')
def delete_document(doc_id):
    doc = db().execute(
        'SELECT * FROM documents WHERE id=? AND user_id=?', (doc_id,get_user()['id'])
    ).fetchone()
    if doc:
        (UPLOAD_DIR / doc['stored_name']).unlink(missing_ok=True)
        db().execute('DELETE FROM documents WHERE id=?', (doc_id,))
        db().commit()
        flash('Document deleted.','success')
    return redirect(url_for('documents'))

@app.route('/admin')
@login_required
@role_required('admin')
def admin():
    stats = {
        key: db().execute(query).fetchone()['n']
        for key, query in {
            'students': "SELECT COUNT(*) n FROM users WHERE role='student'",
            'appointments': 'SELECT COUNT(*) n FROM appointments',
            'pending': "SELECT COUNT(*) n FROM appointments WHERE status='pending'",
            'completed': "SELECT COUNT(*) n FROM appointments WHERE status='completed'"
        }.items()
    }
    rows = db().execute(
        'SELECT a.*,u.full_name,u.email,s.slot_date,s.start_time,s.provider '
        'FROM appointments a JOIN users u ON u.id=a.student_id '
        'JOIN slots s ON s.id=a.slot_id ORDER BY a.created_at DESC'
    ).fetchall()
    students = db().execute(
        "SELECT id,full_name,email,is_active FROM users WHERE role='student' ORDER BY full_name"
    ).fetchall()
    slots = db().execute(
        'SELECT * FROM slots WHERE slot_date>=? ORDER BY slot_date,start_time',
        (date.today().isoformat(),)
    ).fetchall()
    return page('admin.html', stats=stats, appointments=rows, students=students, slots=slots)

@app.post('/admin/appointments/<int:aid>')
@login_required
@role_required('admin')
def admin_appointment(aid):
    status = request.form.get('status')
    note = request.form.get('admin_notes','')[:500]
    if status not in {'confirmed','rejected','completed','cancelled'}:
        abort(400)
    db().execute('UPDATE appointments SET status=?,admin_notes=? WHERE id=?', (status,note,aid))
    db().commit()
    flash('Appointment updated.','success')
    return redirect(url_for('admin'))

@app.post('/admin/slots')
@login_required
@role_required('admin')
def add_slot():
    try:
        slot_date = request.form['slot_date']
        start = request.form['start_time']
        end = request.form['end_time']
        datetime.strptime(slot_date, '%Y-%m-%d')
        if datetime.strptime(end, '%H:%M') <= datetime.strptime(start, '%H:%M') or slot_date < date.today().isoformat():
            raise ValueError('Invalid slot date or time range')
        db().execute(
            'INSERT INTO slots(slot_date,start_time,end_time,provider) VALUES(?,?,?,?)',
            (slot_date,start,end,request.form.get('provider','Campus Health Centre'))
        )
        db().commit()
        flash('Slot added.','success')
    except (sqlite3.IntegrityError,KeyError,ValueError):
        flash('Could not add slot; check the date and time.','danger')
    return redirect(url_for('admin'))

@app.post('/admin/students/<int:uid>')
@login_required
@role_required('admin')
def toggle_student(uid):
    db().execute(
        "UPDATE users SET is_active=CASE is_active WHEN 1 THEN 0 ELSE 1 END "
        "WHERE id=? AND role='student'", (uid,)
    )
    db().commit()
    return redirect(url_for('admin'))

@app.errorhandler(403)
def forbidden(_):
    return render_template('error.html',code=403,message='You do not have permission to access this page.'),403

@app.errorhandler(404)
def not_found(_):
    return render_template('error.html',code=404,message='The requested page was not found.'),404

init_db()

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG','false').lower() == 'true')
