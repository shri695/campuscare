from __future__ import annotations
import os
import re
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

from store import Store

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "local-demo-secret-change-before-deployment")
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024
CORS(app, resources={r"/api/*": {"origins": os.getenv("ALLOWED_ORIGIN", "http://localhost:5173").split(",")}})
store = Store()

DISCLAIMER = "\n\nMedical information disclaimer: I am an AI assistant and cannot diagnose conditions, prescribe treatment or replace a qualified healthcare professional. Please consult a doctor for personal medical advice."
EMERGENCY_WARNING = "🚨 URGENT: Your message may describe a medical emergency. Do not rely on this chatbot. Contact local emergency services immediately (112 in India) or go to the nearest emergency department."
EMERGENCY_TERMS = ["chest pain", "difficulty breathing", "cannot breathe", "can't breathe", "severe bleeding", "unconscious", "stroke symptoms", "suicidal", "overdose", "seizure", "severe allergic reaction"]


def ok(data=None, status=200):
    return jsonify(data or {}), status


def error(message, status=400, details=None):
    payload = {"error": message}
    if details: payload["details"] = details
    return jsonify(payload), status


def token_for(user):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user["id"]), "role": user["role"], "iat": now, "exp": now + timedelta(hours=4)}, app.config["SECRET_KEY"], algorithm="HS256")


def auth_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return error("Authentication required.", 401)
            try:
                claims = jwt.decode(header.split(" ",1)[1], app.config["SECRET_KEY"], algorithms=["HS256"])
                user = store.user_by_id(claims["sub"])
            except (jwt.InvalidTokenError, KeyError, TypeError):
                return error("Invalid or expired access token.", 401)
            if not user or not user.get("is_active", True):
                return error("Account is unavailable.", 401)
            if role and user["role"] != role:
                return error("You do not have permission to access this resource.", 403)
            g.user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def emergency_check(text):
    lowered = text.lower()
    return any(term in lowered for term in EMERGENCY_TERMS)


def gemini_reply(message, history):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None, "AI_NOT_CONFIGURED"
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    system = (
        "You are MediConnect AI, a careful healthcare information assistant. "
        "Provide general educational information in plain language only. Never diagnose, "
        "prescribe, recommend medication dosages, or claim certainty. Encourage professional "
        "assessment for personal symptoms. Ask brief clarifying questions only when useful. "
        "If a message suggests an emergency, tell the user to seek urgent in-person help. "
        "Do not request names, addresses, phone numbers or other identifying information. "
        "Keep answers concise and structured."
    )
    contents=[]
    for item in history[-8:]:
        contents.append({"role":"user","parts":[{"text":item["query"]}]})
        contents.append({"role":"model","parts":[{"text":item["response"]}]})
    contents.append({"role":"user","parts":[{"text":message}]})
    try:
        response=requests.post(url,headers={"x-goog-api-key":api_key,"Content-Type":"application/json"},json={"system_instruction":{"parts":[{"text":system}]},"contents":contents,"generationConfig":{"temperature":0.25,"maxOutputTokens":700}},timeout=25)
        response.raise_for_status()
        data=response.json()
        text="".join(part.get("text","") for part in data["candidates"][0]["content"]["parts"] if "text" in part).strip()
        return (text or "I could not generate a response. Please try again."), None
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None, "AI_PROVIDER_ERROR"


def send_confirmation_email(to_email, patient_name, doctor_name, appointment_date, time_slot):
    key=os.getenv("RESEND_API_KEY","").strip()
    sender=os.getenv("EMAIL_FROM","").strip()
    if not key or not sender or not to_email:
        return False
    try:
        response=requests.post("https://api.resend.com/emails",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json={"from":sender,"to":[to_email],"subject":"MediConnect appointment confirmation","html":f"<p>Hello {patient_name},</p><p>Your appointment with {doctor_name} is confirmed for {appointment_date} at {time_slot}.</p><p>— MediConnect</p>"},timeout=12)
        return response.ok
    except requests.RequestException:
        return False


@app.get("/api/health")
def health():
    return ok({"status":"ok","service":"MediConnect AI API","database":"MongoDB Atlas" if store.mongo else "SQLite local demo","ai_configured":bool(os.getenv("GEMINI_API_KEY"))})


@app.post("/api/auth/register")
def register():
    data=request.get_json(silent=True) or {}
    name=str(data.get("full_name","")).strip()
    email=str(data.get("email","")).strip().lower()
    password=str(data.get("password", ""))
    consent=bool(data.get("consent"))
    if len(name)<2 or len(name)>100 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email) or len(password)<10:
        return error("Enter a valid name/email and a password of at least 10 characters.")
    if not consent:
        return error("Please provide consent before creating an account.")
    if store.user_by_email(email):
        return error("An account with this email already exists.",409)
    try:
        user_id=store.create_user(name,email,generate_password_hash(password),consent)
    except Exception:
        return error("Unable to create this account. Please try again.",409)
    user=store.user_by_id(user_id)
    return ok({"token":token_for(user),"user":{"id":user["id"],"full_name":user["full_name"],"email":user["email"],"role":user["role"]}},201)


@app.post("/api/auth/login")
def login():
    data=request.get_json(silent=True) or {}
    user=store.user_by_email(str(data.get("email","")).strip())
    if not user or not user.get("is_active",True) or not check_password_hash(user["password_hash"],str(data.get("password",""))):
        return error("Invalid email or password.",401)
    return ok({"token":token_for(user),"user":{"id":user["id"],"full_name":user["full_name"],"email":user["email"],"role":user["role"]}})


@app.get("/api/auth/me")
@auth_required()
def me():
    u=g.user
    return ok({"user":{"id":u["id"],"full_name":u["full_name"],"email":u["email"],"role":u["role"]}})


@app.get("/api/profile")
@auth_required()
def get_profile():
    u=g.user
    return ok({"profile":{"id":u["id"],"full_name":u["full_name"],"email":u["email"],"role":u["role"],"consent":u.get("consent",False),"phone":u.get("phone","")}})


@app.put("/api/profile")
@auth_required()
def update_profile():
    data=request.get_json(silent=True) or {}
    name=str(data.get("full_name",g.user["full_name"])).strip()
    phone=str(data.get("phone",g.user.get("phone",""))).strip()[:20]
    if len(name)<2 or len(name)>100: return error("Name must contain 2 to 100 characters.")
    store.update_profile(g.user["id"],name,phone)
    return ok({"message":"Profile updated."})


@app.post("/api/chat")
@auth_required("patient")
def chat():
    data=request.get_json(silent=True) or {}
    message=str(data.get("message","")).strip()
    if not message or len(message)>2000:
        return error("Message must contain between 1 and 2,000 characters.")
    history=store.chat_for_user(g.user["id"],limit=8)
    emergency=emergency_check(message)
    if emergency:
        reply=EMERGENCY_WARNING + DISCLAIMER
    else:
        reply, issue=gemini_reply(message,history)
        if issue=="AI_NOT_CONFIGURED":
            return error("The AI assistant is not configured yet. Add GEMINI_API_KEY to backend/.env and restart the server.",503)
        if issue:
            return error("The AI service is temporarily unavailable. Please try again later or contact a healthcare professional.",502)
        reply += DISCLAIMER
    store.save_chat(g.user["id"],message,reply,emergency)
    return ok({"reply":reply,"emergency":emergency,"disclaimer":DISCLAIMER.strip()})


@app.get("/api/chat/history")
@auth_required("patient")
def chat_history():
    return ok({"messages":store.chat_for_user(g.user["id"],limit=50)})


@app.get("/api/doctors")
def doctors():
    query=request.args.get("q","").strip()[:80]
    specialization=request.args.get("specialization","").strip()[:80]
    return ok({"doctors":store.list_doctors(query,specialization)})


@app.get("/api/doctors/<doctor_id>")
def doctor_detail(doctor_id):
    doctor=store.doctor_by_id(doctor_id)
    if not doctor: return error("Doctor not found.",404)
    return ok({"doctor":doctor,"suggested_slots":["09:00","10:30","12:00","14:00","15:30"]})


@app.get("/api/hospitals/nearby")
@auth_required("patient")
def nearby_hospitals():
    location=request.args.get("location","Bengaluru").strip()[:120]
    key=os.getenv("MAPS_API_KEY","").strip()
    if not key:
        return ok({"hospitals":[],"maps_search_url":"https://www.google.com/maps/search/?api=1&query="+requests.utils.quote("hospitals near "+location),"message":"Maps API key not configured; use the Google Maps search link."})
    try:
        resp=requests.post("https://places.googleapis.com/v1/places:searchText",headers={"X-Goog-Api-Key":key,"X-Goog-FieldMask":"places.displayName,places.formattedAddress,places.googleMapsUri,places.location"},json={"textQuery":f"hospitals near {location}","maxResultCount":8},timeout=12)
        resp.raise_for_status()
        return ok({"hospitals":resp.json().get("places",[])})
    except requests.RequestException:
        return ok({"hospitals":[],"maps_search_url":"https://www.google.com/maps/search/?api=1&query="+requests.utils.quote("hospitals near "+location),"message":"Maps lookup is temporarily unavailable."})


@app.route("/api/appointments",methods=["GET","POST"])
@auth_required("patient")
def appointments():
    if request.method=="GET": return ok({"appointments":store.appointments_for_user(g.user["id"])})
    data=request.get_json(silent=True) or {}
    doctor_id=str(data.get("doctor_id","")); appt_date=str(data.get("date","")); time_slot=str(data.get("time_slot","")); reason=str(data.get("reason","General consultation")).strip()
    try: dt=datetime.strptime(appt_date,"%Y-%m-%d").date()
    except ValueError: return error("Appointment date must use YYYY-MM-DD.")
    if dt < datetime.now().date(): return error("Appointment date must be in the future.")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d",time_slot): return error("Select a valid appointment time.")
    if len(reason)<5 or len(reason)>500: return error("Reason must be between 5 and 500 characters.")
    doctor=store.doctor_by_id(doctor_id)
    if not doctor: return error("Doctor not found.",404)
    try:
        appointment_id=store.create_appointment(g.user["id"],doctor_id,appt_date,time_slot,reason)
    except Exception:
        return error("This doctor and time slot is already booked. Please select another slot.",409)
    email_sent=send_confirmation_email(g.user["email"],g.user["full_name"],doctor["name"],appt_date,time_slot)
    return ok({"id":appointment_id,"status":"confirmed","email_sent":email_sent,"message":"Appointment confirmed."},201)


@app.post("/api/appointments/<appointment_id>/cancel")
@auth_required("patient")
def cancel_appointment(appointment_id):
    if not store.cancel_appointment(appointment_id,g.user["id"]): return error("Appointment not found or cannot be cancelled.",404)
    return ok({"message":"Appointment cancelled."})


@app.route("/api/health-records",methods=["GET","POST"])
@auth_required("patient")
def health_records():
    if request.method=="GET": return ok({"records":store.records_for_user(g.user["id"])})
    data=request.get_json(silent=True) or {}
    kind=str(data.get("record_type","")).strip()[:60]; value=str(data.get("value","")).strip()[:200]; notes=str(data.get("notes","")).strip()[:500]; recorded_on=str(data.get("recorded_on",datetime.now().date().isoformat()))
    if not kind or not value: return error("Record type and value are required.")
    try: datetime.strptime(recorded_on,"%Y-%m-%d")
    except ValueError: return error("Date must use YYYY-MM-DD.")
    record_id=store.add_record(g.user["id"],kind,value,notes,recorded_on)
    return ok({"id":record_id,"message":"Health record saved."},201)


@app.put("/api/health-records/<record_id>")
@auth_required("patient")
def update_health_record(record_id):
    data=request.get_json(silent=True) or {}
    kind=str(data.get("record_type","")).strip()[:60]; value=str(data.get("value","")).strip()[:200]; notes=str(data.get("notes","")).strip()[:500]; recorded_on=str(data.get("recorded_on",datetime.now().date().isoformat()))
    if not kind or not value: return error("Record type and value are required.")
    try: datetime.strptime(recorded_on,"%Y-%m-%d")
    except ValueError: return error("Date must use YYYY-MM-DD.")
    if not store.update_record(record_id,g.user["id"],kind,value,notes,recorded_on): return error("Record not found.",404)
    return ok({"message":"Record updated."})


@app.delete("/api/health-records/<record_id>")
@auth_required("patient")
def delete_health_record(record_id):
    if not store.delete_record(record_id,g.user["id"]): return error("Record not found.",404)
    return ok({"message":"Record deleted."})


@app.get("/api/dashboard")
@auth_required("patient")
def dashboard():
    return ok({"summary":store.dashboard(g.user["id"])})


@app.post("/api/admin/doctors")
@auth_required("admin")
def admin_create_doctor():
    data=request.get_json(silent=True) or {}
    required=["name","specialization","hospital","city"]
    if any(not str(data.get(k," ")).strip() for k in required): return error("Name, specialization, hospital and city are required.")
    try:
        doctor_id=store.create_doctor({"name":str(data["name"]).strip(),"specialization":str(data["specialization"]).strip(),"hospital":str(data["hospital"]).strip(),"city":str(data["city"]).strip(),"experience":int(data.get("experience",0)),"fee":int(data.get("fee",0)),"hours":str(data.get("hours","By appointment")),"bio":str(data.get("bio","")),"lat":float(data.get("lat",0) or 0),"lng":float(data.get("lng",0) or 0)})
        return ok({"id":doctor_id,"message":"Doctor added."},201)
    except (ValueError,TypeError): return error("Experience, fee and coordinates must be numeric.")


@app.put("/api/admin/doctors/<doctor_id>")
@auth_required("admin")
def admin_update_doctor(doctor_id):
    data=request.get_json(silent=True) or {}
    allowed={k:data[k] for k in ["name","specialization","hospital","city","experience","fee","hours","bio","lat","lng","is_active"] if k in data}
    if not allowed: return error("No editable doctor fields supplied.")
    if not store.update_doctor(doctor_id,allowed): return error("Doctor not found.",404)
    return ok({"message":"Doctor updated."})


@app.patch("/api/admin/users/<user_id>")
@auth_required("admin")
def admin_update_user(user_id):
    data=request.get_json(silent=True) or {}
    if "is_active" not in data or not isinstance(data["is_active"],bool): return error("is_active must be a boolean value.")
    if not store.set_user_active(user_id,data["is_active"]): return error("Patient account not found.",404)
    return ok({"message":"Patient account status updated."})


@app.get("/api/admin/stats")
@auth_required("admin")
def admin_stats():
    return ok({"stats":store.admin_stats(),"appointments":store.all_appointments(),"patients":store.list_patients()})


@app.get("/api/admin/users")
@auth_required("admin")
def admin_users():
    return ok({"users":store.list_patients()})


@app.patch("/api/admin/appointments/<appointment_id>")
@auth_required("admin")
def admin_appointment_update(appointment_id):
    data=request.get_json(silent=True) or {}
    if data.get("status")!="cancelled": return error("Only cancellation is enabled in this starter release.")
    if not store.cancel_appointment(appointment_id): return error("Appointment not found or already final.",404)
    return ok({"message":"Appointment cancelled by administrator."})


@app.errorhandler(413)
def too_large(_): return error("Request body is too large.",413)


if __name__=="__main__":
    app.run(host="127.0.0.1",port=int(os.getenv("PORT","5000")),debug=os.getenv("FLASK_DEBUG","false").lower()=="true")
