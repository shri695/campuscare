from datetime import date, timedelta


def register(client, name="Test Patient", email="patient@example.com"):
    response = client.post("/api/auth/register", json={
        "full_name": name,
        "email": email,
        "password": "StrongDemoPass123!",
        "consent": True,
    })
    assert response.status_code == 201
    return response.get_json()["token"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint_and_doctor_directory(client):
    c, _ = client
    health = c.get("/api/health")
    assert health.status_code == 200
    assert health.get_json()["database"] == "SQLite local demo"
    doctors = c.get("/api/doctors?q=Ananya")
    assert doctors.status_code == 200
    assert any("Ananya" in doctor["name"] for doctor in doctors.get_json()["doctors"])


def test_registration_duplicate_and_login(client):
    c, _ = client
    token = register(c)
    assert c.get("/api/auth/me", headers=headers(token)).status_code == 200
    duplicate = c.post("/api/auth/register", json={
        "full_name": "Another Patient", "email": "patient@example.com",
        "password": "StrongDemoPass123!", "consent": True,
    })
    assert duplicate.status_code == 409
    login = c.post("/api/auth/login", json={"email":"patient@example.com","password":"StrongDemoPass123!"})
    assert login.status_code == 200
    assert login.get_json()["user"]["role"] == "patient"


def test_consent_is_required(client):
    c, _ = client
    response = c.post("/api/auth/register", json={
        "full_name":"No Consent", "email":"no-consent@example.com",
        "password":"StrongDemoPass123!", "consent":False,
    })
    assert response.status_code == 400


def test_appointment_double_booking_and_cancel(client):
    c, module = client
    patient_token = register(c)
    doctor = c.get("/api/doctors").get_json()["doctors"][0]
    payload = {
        "doctor_id": doctor["id"],
        "date": (date.today() + timedelta(days=3)).isoformat(),
        "time_slot": "10:30",
        "reason": "Routine general consultation",
    }
    first = c.post("/api/appointments", json=payload, headers=headers(patient_token))
    assert first.status_code == 201
    second = c.post("/api/appointments", json=payload, headers=headers(patient_token))
    assert second.status_code == 409
    appointment_id = c.get("/api/appointments", headers=headers(patient_token)).get_json()["appointments"][0]["id"]
    cancelled = c.post(f"/api/appointments/{appointment_id}/cancel", json={}, headers=headers(patient_token))
    assert cancelled.status_code == 200
    again = c.post("/api/appointments", json=payload, headers=headers(patient_token))
    assert again.status_code == 201


def test_health_records_are_user_scoped(client):
    c, _ = client
    token_one = register(c, email="one@example.com")
    token_two = register(c, name="Second Patient", email="two@example.com")
    created = c.post("/api/health-records", json={
        "record_type":"General note", "value":"Demo data only", "recorded_on":date.today().isoformat()
    }, headers=headers(token_one))
    assert created.status_code == 201
    record_id = created.get_json()["id"]
    denied = c.delete(f"/api/health-records/{record_id}", headers=headers(token_two))
    assert denied.status_code == 404
    visible = c.get("/api/health-records", headers=headers(token_one)).get_json()["records"]
    assert len(visible) == 1


def test_emergency_chat_guard_runs_before_ai(client):
    c, _ = client
    token = register(c)
    response = c.post("/api/chat", json={"message":"I have severe chest pain and difficulty breathing"}, headers=headers(token))
    assert response.status_code == 200
    assert response.get_json()["emergency"] is True
    assert "112" in response.get_json()["reply"]


def test_chat_requires_ai_key_for_non_emergency_request(client):
    c, _ = client
    token = register(c)
    response = c.post("/api/chat", json={"message":"What is a routine check-up?"}, headers=headers(token))
    assert response.status_code == 503


def test_admin_routes_are_role_protected(client):
    c, _ = client
    patient_token = register(c)
    denied = c.get("/api/admin/stats", headers=headers(patient_token))
    assert denied.status_code == 403
    admin_login = c.post("/api/auth/login", json={
        "email":"admin@mediconnect.local", "password":"AdminDemoPassword!123"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.get_json()["token"]
    stats = c.get("/api/admin/stats", headers=headers(admin_token))
    assert stats.status_code == 200
    assert stats.get_json()["stats"]["patients"] == 1


def test_profile_update(client):
    c, _ = client
    token = register(c)
    response = c.put("/api/profile", json={"full_name":"Updated Patient","phone":"9876543210"}, headers=headers(token))
    assert response.status_code == 200
    profile = c.get("/api/profile", headers=headers(token)).get_json()["profile"]
    assert profile["full_name"] == "Updated Patient"
    assert profile["phone"] == "9876543210"


def test_admin_can_add_doctor_and_update_patient_status(client):
    c, _ = client
    patient_token = register(c)
    patient_id = c.get("/api/admin/users", headers=headers(
        c.post("/api/auth/login", json={"email":"admin@mediconnect.local","password":"AdminDemoPassword!123"}).get_json()["token"]
    )).get_json()["users"][0]["id"]
    admin_token = c.post("/api/auth/login", json={
        "email":"admin@mediconnect.local", "password":"AdminDemoPassword!123"
    }).get_json()["token"]
    created = c.post("/api/admin/doctors", json={
        "name":"Dr. Demo Doctor", "specialization":"General Physician",
        "hospital":"Demo Clinic", "city":"Bengaluru", "experience":5, "fee":300,
    }, headers=headers(admin_token))
    assert created.status_code == 201
    changed = c.patch(f"/api/admin/users/{patient_id}", json={"is_active":False}, headers=headers(admin_token))
    assert changed.status_code == 200
    denied = c.get("/api/auth/me", headers=headers(patient_token))
    assert denied.status_code == 401
