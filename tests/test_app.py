import pytest
from app import app as flask_app

@pytest.fixture()
def client(tmp_path):
    import app as module
    db_path = tmp_path / 'test.db'
    old_path = module.DB_PATH
    module.DB_PATH = str(db_path)
    module.init_db()
    flask_app.config.update(TESTING=True, SECRET_KEY='test-secret')
    with flask_app.test_client() as test_client:
        yield test_client
    module.DB_PATH = old_path

def csrf(client):
    client.get('/login')
    with client.session_transaction() as session:
        return session['csrf']

def register_and_login(client, email='student@example.com'):
    token = csrf(client)
    client.post('/register', data={'csrf_token':token,'full_name':'Test Student','email':email,'password':'Student123'})
    token = csrf(client)
    return client.post('/login', data={'csrf_token':token,'email':email,'password':'Student123'}, follow_redirects=True)

def test_register_login_dashboard(client):
    response = register_and_login(client)
    assert response.status_code == 200
    assert b'Good day' in response.data

def test_student_pages_and_wellness(client):
    register_and_login(client)
    token = csrf(client)
    response = client.post('/wellness', data={'csrf_token':token,'record_date':'2026-11-25','water_ml':'1800','sleep_hours':'7.5','exercise_minutes':'25','mood':'Good'}, follow_redirects=True)
    assert response.status_code == 200 and b'1800 ml water' in response.data
    assert client.get('/resources').status_code == 200
    assert client.get('/profile').status_code == 200

def test_admin_login_and_dashboard(client):
    token = csrf(client)
    response = client.post('/login', data={'csrf_token':token,'email':'admin@campuscare.local','password':'Admin@12345'}, follow_redirects=True)
    assert response.status_code == 200 and b'Admin dashboard' in response.data

def test_csrf_rejects_missing_token(client):
    response = client.post('/register', data={'full_name':'Test Student','email':'x@example.com','password':'Student123'})
    assert response.status_code == 403
