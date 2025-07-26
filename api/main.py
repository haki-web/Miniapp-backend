import os
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "token_uri": "https://oauth2.googleapis.com/token"
        })
        firebase_admin.initialize_app(cred)
        print("✅ Firebase connected")
    db = firestore.client()
except Exception as e:
    print("❌ Firebase Init Error:", e)

class PointsRequest(BaseModel):
    user_id: str
    amount: int

class ReferralRequest(BaseModel):
    user_id: str
    referral_id: str

@app.get("/")
def home():
    return {"status": "ok", "message": "Firebase FastAPI Backend Running!"}

@app.get("/points/{user_id}")
def get_points(user_id: str):
    doc = db.collection("users").document(user_id).get()
    if doc.exists:
        return {"user_id": user_id, "points": doc.to_dict().get("points", 0)}
    return {"user_id": user_id, "points": 0}

@app.post("/add_points")
def add_points(data: PointsRequest):
    user_ref = db.collection("users").document(data.user_id)
    doc = user_ref.get()
    current_points = doc.to_dict().get("points", 0) if doc.exists else 0
    new_points = current_points + data.amount
    user_ref.set({"points": new_points}, merge=True)
    return {"user_id": data.user_id, "points": new_points}

@app.post("/referral")
def referral(data: ReferralRequest):
    if data.user_id == data.referral_id:
        return {"error": "You cannot refer yourself"}

    ref_user = db.collection("users").document(data.user_id)
    ref_doc = ref_user.get()
    referred_users = ref_doc.to_dict().get("referrals", []) if ref_doc.exists else []

    if data.referral_id not in referred_users:
        referred_users.append(data.referral_id)
        points = ref_doc.to_dict().get("points", 0) if ref_doc.exists else 0
        points += 100
        ref_user.set({"points": points, "referrals": referred_users}, merge=True)
        return {
            "message": "Referral added",
            "points": points,
            "referrals": referred_users
        }
    return {
        "message": "Already referred",
        "points": ref_doc.to_dict().get("points", 0),
        "referrals": referred_users
      }
