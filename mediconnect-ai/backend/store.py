"""Persistence adapter: MongoDB Atlas when MONGODB_URI is configured, SQLite for local demo/CI."""
from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from werkzeug.security import generate_password_hash

DOCTORS = [
    {"name":"Dr. Ananya Rao","specialization":"General Physician","hospital":"NHCE Community Clinic","city":"Bengaluru","experience":9,"fee":400,"hours":"Mon–Sat · 9:00 AM–1:00 PM","lat":12.9352,"lng":77.6245,"bio":"Primary care, preventive check-ups and common health concerns.","is_active":True},
    {"name":"Dr. Karthik Menon","specialization":"Cardiologist","hospital":"Lakeview Heart Centre","city":"Bengaluru","experience":14,"fee":900,"hours":"Mon–Fri · 10:00 AM–2:00 PM","lat":12.9716,"lng":77.5946,"bio":"Cardiovascular health assessment and long-term heart-care planning.","is_active":True},
    {"name":"Dr. Meera Nair","specialization":"Dermatologist","hospital":"GreenCross Medical Centre","city":"Bengaluru","experience":8,"fee":650,"hours":"Tue–Sun · 11:00 AM–4:00 PM","lat":12.9279,"lng":77.6271,"bio":"Skin, hair and general dermatology consultations.","is_active":True},
    {"name":"Dr. Vikram Shah","specialization":"Orthopedician","hospital":"OrthoCare Hospital","city":"Bengaluru","experience":12,"fee":700,"hours":"Mon–Sat · 8:30 AM–12:30 PM","lat":12.9141,"lng":77.6411,"bio":"Joint, muscle and sports-injury assessment.","is_active":True},
    {"name":"Dr. Priya Shetty","specialization":"Psychologist","hospital":"MindWell Centre","city":"Bengaluru","experience":7,"fee":600,"hours":"Mon–Fri · 12:00 PM–6:00 PM","lat":12.9560,"lng":77.6010,"bio":"Supportive mental-wellbeing and stress-management consultations.","is_active":True},
    {"name":"Dr. Rahul Iyer","specialization":"ENT Specialist","hospital":"CityCare Hospital","city":"Bengaluru","experience":11,"fee":550,"hours":"Mon–Sat · 10:00 AM–1:00 PM","lat":12.9820,"lng":77.6030,"bio":"Ear, nose and throat consultations.","is_active":True},
    {"name":"Dr. Farah Khan","specialization":"Gynecologist","hospital":"Sakhi Women’s Health","city":"Bengaluru","experience":10,"fee":750,"hours":"Mon–Fri · 9:00 AM–2:00 PM","lat":12.9230,"lng":77.6200,"bio":"Women’s health consultations and preventive care.","is_active":True},
    {"name":"Dr. Arjun Rao","specialization":"Pediatrician","hospital":"LittleSteps Children’s Clinic","city":"Bengaluru","experience":13,"fee":700,"hours":"Mon–Sat · 9:30 AM–1:30 PM","lat":12.9400,"lng":77.6100,"bio":"Child health, growth and routine pediatric care.","is_active":True},
]

class Store:
    def __init__(self) -> None:
        self.mongo = False
        self.client = None
        uri = os.getenv("MONGODB_URI", "").strip()
        if uri:
            try:
                from pymongo import MongoClient, ASCENDING
                self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
                self.client.admin.command("ping")
                db_name = os.getenv("MONGODB_DATABASE", "mediconnect")
                self.db = self.client[db_name]
                self.mongo = True
                self.db.users.create_index("email", unique=True)
                self.db.doctors.create_index([("specialization", ASCENDING)])
                self.db.doctors.create_index([("location", "2dsphere")])
                self.db.appointments.create_index(
                    [("doctor_id", ASCENDING), ("date", ASCENDING), ("time_slot", ASCENDING)],
                    unique=True,
                    partialFilterExpression={"status": "confirmed"},
                    name="uq_active_doctor_slot",
                )
                self.db.appointments.create_index([("user_id", ASCENDING)])
                self.db.health_records.create_index([("user_id", ASCENDING), ("recorded_on", -1)])
                self.db.chat_history.create_index([("user_id", ASCENDING), ("timestamp", -1)])
            except Exception as exc:
                raise RuntimeError(f"Could not connect to MongoDB Atlas: {exc}") from exc
        else:
            self.path = os.getenv("SQLITE_PATH", str(Path(__file__).resolve().parent / "instance" / "mediconnect.db"))
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            self._init_sqlite()
        self.seed_doctors()
        self.seed_admin()

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_sqlite(self):
        with self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'patient', consent INTEGER NOT NULL DEFAULT 0, is_active INTEGER NOT NULL DEFAULT 1, phone TEXT DEFAULT '', created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS doctors(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, specialization TEXT NOT NULL, hospital TEXT NOT NULL, city TEXT NOT NULL, experience INTEGER NOT NULL, fee INTEGER NOT NULL, hours TEXT NOT NULL, lat REAL, lng REAL, bio TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), doctor_id INTEGER NOT NULL REFERENCES doctors(id), date TEXT NOT NULL, time_slot TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'confirmed', created_at TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS uq_active_doctor_slot ON appointments(doctor_id,date,time_slot) WHERE status='confirmed';
            CREATE TABLE IF NOT EXISTS health_records(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), record_type TEXT NOT NULL, value TEXT NOT NULL, notes TEXT DEFAULT '', recorded_on TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS chat_history(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), query TEXT NOT NULL, response TEXT NOT NULL, emergency_flag INTEGER NOT NULL DEFAULT 0, timestamp TEXT NOT NULL);
            """)

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def seed_doctors(self):
        if self.mongo:
            if self.db.doctors.count_documents({}) == 0:
                from pymongo import GEOSPHERE
                docs = []
                for d in DOCTORS:
                    row = dict(d)
                    row["location"] = {"type":"Point", "coordinates":[d["lng"], d["lat"]]}
                    docs.append(row)
                self.db.doctors.insert_many(docs)
        else:
            with self._conn() as c:
                if c.execute("SELECT COUNT(*) n FROM doctors").fetchone()["n"] == 0:
                    c.executemany("INSERT INTO doctors(name,specialization,hospital,city,experience,fee,hours,lat,lng,bio,is_active) VALUES(:name,:specialization,:hospital,:city,:experience,:fee,:hours,:lat,:lng,:bio,:is_active)", DOCTORS)

    def seed_admin(self):
        email = os.getenv("ADMIN_EMAIL", "admin@mediconnect.local").lower()
        password = os.getenv("ADMIN_PASSWORD", "ChangeThisAdminPassword!")
        if self.mongo:
            if not self.db.users.find_one({"role":"admin"}):
                self.db.users.insert_one({"full_name":"MediConnect Administrator","email":email,"password_hash":generate_password_hash(password),"role":"admin","consent":True,"is_active":True,"created_at":self.now()})
        else:
            with self._conn() as c:
                if not c.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
                    c.execute("INSERT INTO users(full_name,email,password_hash,role,consent,created_at) VALUES(?,?,?,?,?,?)",("MediConnect Administrator",email,generate_password_hash(password),"admin",1,self.now()))

    def create_user(self, full_name, email, password_hash, consent):
        row = {"full_name":full_name,"email":email.lower(),"password_hash":password_hash,"role":"patient","consent":bool(consent),"is_active":True,"created_at":self.now()}
        if self.mongo:
            result = self.db.users.insert_one(row)
            row["_id"] = result.inserted_id
            return str(result.inserted_id)
        with self._conn() as c:
            cur = c.execute("INSERT INTO users(full_name,email,password_hash,role,consent,created_at) VALUES(?,?,?,?,?,?)",(full_name,email.lower(),password_hash,"patient",int(bool(consent)),row["created_at"]))
            return str(cur.lastrowid)

    def user_by_email(self, email):
        if self.mongo:
            row = self.db.users.find_one({"email":email.lower()})
            if row: row["id"] = str(row.pop("_id"))
            return row
        with self._conn() as c:
            row = c.execute("SELECT * FROM users WHERE email=?",(email.lower(),)).fetchone()
            return dict(row) if row else None

    def user_by_id(self, user_id):
        if self.mongo:
            from bson import ObjectId
            try: row = self.db.users.find_one({"_id":ObjectId(user_id)})
            except Exception: return None
            if row: row["id"] = str(row.pop("_id"))
            return row
        with self._conn() as c:
            row = c.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
            return dict(row) if row else None

    def list_doctors(self, query="", specialization=""):
        if self.mongo:
            criteria = {}
            criteria["is_active"] = {"$ne":False}
            if query: criteria["$or"] = [{"name":{"$regex":query,"$options":"i"}},{"hospital":{"$regex":query,"$options":"i"}},{"city":{"$regex":query,"$options":"i"}}]
            if specialization: criteria["specialization"] = specialization
            rows = list(self.db.doctors.find(criteria).sort("name",1))
            for x in rows: x["id"] = str(x.pop("_id")); x.pop("location",None)
            return rows
        with self._conn() as c:
            sql = "SELECT * FROM doctors WHERE is_active=1"; args=[]
            if query:
                sql += " AND (name LIKE ? OR hospital LIKE ? OR city LIKE ?)"; args += [f"%{query}%"]*3
            if specialization: sql += " AND specialization=?"; args.append(specialization)
            return [dict(x) for x in c.execute(sql+" ORDER BY name",args).fetchall()]

    def doctor_by_id(self, doctor_id):
        if self.mongo:
            from bson import ObjectId
            try: row = self.db.doctors.find_one({"_id":ObjectId(doctor_id),"is_active":{"$ne":False}})
            except Exception: return None
            if row: row["id"] = str(row.pop("_id")); row.pop("location",None)
            return row
        with self._conn() as c:
            row=c.execute("SELECT * FROM doctors WHERE id=? AND is_active=1",(doctor_id,)).fetchone(); return dict(row) if row else None

    def create_appointment(self, user_id, doctor_id, date, time_slot, reason):
        now=self.now()
        if self.mongo:
            from bson import ObjectId
            row={"user_id":ObjectId(user_id),"doctor_id":ObjectId(doctor_id),"date":date,"time_slot":time_slot,"reason":reason,"status":"confirmed","created_at":now}
            result=self.db.appointments.insert_one(row); return str(result.inserted_id)
        with self._conn() as c:
            cur=c.execute("INSERT INTO appointments(user_id,doctor_id,date,time_slot,reason,status,created_at) VALUES(?,?,?,?,?,'confirmed',?)",(user_id,doctor_id,date,time_slot,reason,now)); return str(cur.lastrowid)

    def appointments_for_user(self, user_id):
        if self.mongo:
            from bson import ObjectId
            rows=list(self.db.appointments.find({"user_id":ObjectId(user_id)}).sort([("date",-1),("time_slot",-1)]))
            for x in rows: x["id"]=str(x.pop("_id")); x["user_id"]=str(x["user_id"]); x["doctor_id"]=str(x["doctor_id"]); x["doctor"]=self.doctor_by_id(x["doctor_id"])
            return rows
        with self._conn() as c:
            rows=c.execute("SELECT a.*,d.name doctor_name,d.specialization,d.hospital,d.city,d.fee FROM appointments a JOIN doctors d ON d.id=a.doctor_id WHERE a.user_id=? ORDER BY a.date DESC,a.time_slot DESC",(user_id,)).fetchall(); return [dict(x) for x in rows]

    def all_appointments(self):
        if self.mongo:
            rows=list(self.db.appointments.find().sort("created_at",-1))
            for x in rows:
                x["id"]=str(x.pop("_id")); x["user_id"]=str(x["user_id"]); x["doctor_id"]=str(x["doctor_id"]); patient=self.user_by_id(x["user_id"]); x["patient"]={k:patient.get(k) for k in ("id","full_name","email","role")} if patient else None; x["doctor"]=self.doctor_by_id(x["doctor_id"])
            return rows
        with self._conn() as c:
            rows=c.execute("SELECT a.*,u.full_name patient_name,u.email patient_email,d.name doctor_name FROM appointments a JOIN users u ON u.id=a.user_id JOIN doctors d ON d.id=a.doctor_id ORDER BY a.created_at DESC").fetchall(); return [dict(x) for x in rows]

    def cancel_appointment(self, appointment_id, user_id=None):
        if self.mongo:
            from bson import ObjectId
            try: oid=ObjectId(appointment_id)
            except Exception: return False
            filt={"_id":oid,"status":"confirmed"}
            if user_id: filt["user_id"]=ObjectId(user_id)
            return self.db.appointments.update_one(filt,{"$set":{"status":"cancelled"}}).modified_count==1
        with self._conn() as c:
            if user_id:
                cur=c.execute("UPDATE appointments SET status='cancelled' WHERE id=? AND user_id=? AND status='confirmed'",(appointment_id,user_id))
            else:
                cur=c.execute("UPDATE appointments SET status='cancelled' WHERE id=? AND status='confirmed'",(appointment_id,))
            return cur.rowcount==1

    def add_record(self,user_id,record_type,value,notes,recorded_on):
        row={"user_id":user_id,"record_type":record_type,"value":value,"notes":notes,"recorded_on":recorded_on,"created_at":self.now()}
        if self.mongo:
            from bson import ObjectId
            row["user_id"]=ObjectId(user_id); result=self.db.health_records.insert_one(row); return str(result.inserted_id)
        with self._conn() as c:
            cur=c.execute("INSERT INTO health_records(user_id,record_type,value,notes,recorded_on,created_at) VALUES(?,?,?,?,?,?)",(user_id,record_type,value,notes,recorded_on,row["created_at"])); return str(cur.lastrowid)

    def records_for_user(self,user_id):
        if self.mongo:
            from bson import ObjectId
            rows=list(self.db.health_records.find({"user_id":ObjectId(user_id)}).sort("recorded_on",-1))
            for x in rows: x["id"]=str(x.pop("_id")); x["user_id"]=str(x["user_id"])
            return rows
        with self._conn() as c:
            return [dict(x) for x in c.execute("SELECT * FROM health_records WHERE user_id=? ORDER BY recorded_on DESC",(user_id,)).fetchall()]

    def delete_record(self,record_id,user_id):
        if self.mongo:
            from bson import ObjectId
            try: oid=ObjectId(record_id)
            except Exception: return False
            return self.db.health_records.delete_one({"_id":oid,"user_id":ObjectId(user_id)}).deleted_count==1
        with self._conn() as c:
            cur=c.execute("DELETE FROM health_records WHERE id=? AND user_id=?",(record_id,user_id)); return cur.rowcount==1

    def save_chat(self,user_id,query,response,emergency):
        row={"user_id":user_id,"query":query,"response":response,"emergency_flag":bool(emergency),"timestamp":self.now()}
        if self.mongo:
            from bson import ObjectId
            row["user_id"]=ObjectId(user_id); self.db.chat_history.insert_one(row)
        else:
            with self._conn() as c: c.execute("INSERT INTO chat_history(user_id,query,response,emergency_flag,timestamp) VALUES(?,?,?,?,?)",(user_id,query,response,int(bool(emergency)),row["timestamp"]))

    def chat_for_user(self,user_id,limit=30):
        if self.mongo:
            from bson import ObjectId
            rows=list(self.db.chat_history.find({"user_id":ObjectId(user_id)}).sort("timestamp",-1).limit(limit))
            for x in rows: x["id"]=str(x.pop("_id")); x["user_id"]=str(x["user_id"])
            return rows[::-1]
        with self._conn() as c: return [dict(x) for x in c.execute("SELECT * FROM chat_history WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",(user_id,limit)).fetchall()][::-1]

    def update_profile(self,user_id,full_name,phone):
        if self.mongo:
            from bson import ObjectId
            self.db.users.update_one({"_id":ObjectId(user_id)},{"$set":{"full_name":full_name,"phone":phone}})
        else:
            with self._conn() as c: c.execute("UPDATE users SET full_name=?,phone=? WHERE id=?",(full_name,phone,user_id))

    def update_record(self,record_id,user_id,record_type,value,notes,recorded_on):
        if self.mongo:
            from bson import ObjectId
            try: oid=ObjectId(record_id)
            except Exception: return False
            return self.db.health_records.update_one({"_id":oid,"user_id":ObjectId(user_id)},{"$set":{"record_type":record_type,"value":value,"notes":notes,"recorded_on":recorded_on}}).modified_count==1
        with self._conn() as c:
            cur=c.execute("UPDATE health_records SET record_type=?,value=?,notes=?,recorded_on=? WHERE id=? AND user_id=?",(record_type,value,notes,recorded_on,record_id,user_id)); return cur.rowcount==1

    def create_doctor(self,data):
        data={**data,"is_active":True}
        if self.mongo:
            if data.get("lat") and data.get("lng"): data["location"]={"type":"Point","coordinates":[data["lng"],data["lat"]]}
            result=self.db.doctors.insert_one(data); return str(result.inserted_id)
        with self._conn() as c:
            cur=c.execute("INSERT INTO doctors(name,specialization,hospital,city,experience,fee,hours,lat,lng,bio,is_active) VALUES(:name,:specialization,:hospital,:city,:experience,:fee,:hours,:lat,:lng,:bio,1)",data); return str(cur.lastrowid)

    def update_doctor(self,doctor_id,fields):
        if self.mongo:
            from bson import ObjectId
            try: oid=ObjectId(doctor_id)
            except Exception: return False
            if "lat" in fields or "lng" in fields:
                existing=self.db.doctors.find_one({"_id":oid}) or {}
                lat=fields.get("lat",existing.get("lat",0)); lng=fields.get("lng",existing.get("lng",0))
                fields["location"]={"type":"Point","coordinates":[lng,lat]}
            return self.db.doctors.update_one({"_id":oid},{"$set":fields}).matched_count==1
        allowed={k:v for k,v in fields.items() if k in {"name","specialization","hospital","city","experience","fee","hours","bio","lat","lng","is_active"}}
        if not allowed: return False
        sql="UPDATE doctors SET "+", ".join(f"{k}=?" for k in allowed)+" WHERE id=?"
        with self._conn() as c:
            cur=c.execute(sql,[*allowed.values(),doctor_id]); return cur.rowcount==1

    def dashboard(self,user_id):
        appointments=self.appointments_for_user(user_id)
        records=self.records_for_user(user_id)[:5]
        return {"appointments_total":len(appointments),"upcoming_appointments":sum(1 for a in appointments if a["status"]=="confirmed" and a["date"]>=datetime.now().date().isoformat()),"records_total":len(self.records_for_user(user_id)),"next_appointment":next((a for a in sorted(appointments,key=lambda x:(x["date"],x["time_slot"])) if a["status"]=="confirmed" and a["date"]>=datetime.now().date().isoformat()),None),"recent_records":records}

    def admin_stats(self):
        if self.mongo:
            return {"patients":self.db.users.count_documents({"role":"patient"}),"doctors":self.db.doctors.count_documents({}),"appointments":self.db.appointments.count_documents({}),"active_appointments":self.db.appointments.count_documents({"status":"confirmed"})}
        with self._conn() as c:
            return {"patients":c.execute("SELECT COUNT(*) n FROM users WHERE role='patient'").fetchone()["n"],"doctors":c.execute("SELECT COUNT(*) n FROM doctors").fetchone()["n"],"appointments":c.execute("SELECT COUNT(*) n FROM appointments").fetchone()["n"],"active_appointments":c.execute("SELECT COUNT(*) n FROM appointments WHERE status='confirmed'").fetchone()["n"]}

    def set_user_active(self,user_id,is_active):
        if self.mongo:
            from bson import ObjectId
            try: oid=ObjectId(user_id)
            except Exception: return False
            return self.db.users.update_one({"_id":oid,"role":"patient"},{"$set":{"is_active":bool(is_active)}}).matched_count==1
        with self._conn() as c:
            cur=c.execute("UPDATE users SET is_active=? WHERE id=? AND role='patient'",(int(bool(is_active)),user_id)); return cur.rowcount==1

    def list_patients(self):
        if self.mongo:
            rows=list(self.db.users.find({"role":"patient"},{"password_hash":0}).sort("created_at",-1))
            for x in rows: x["id"]=str(x.pop("_id"))
            return rows
        with self._conn() as c: return [dict(x) for x in c.execute("SELECT id,full_name,email,role,consent,is_active,created_at FROM users WHERE role='patient' ORDER BY created_at DESC").fetchall()]
