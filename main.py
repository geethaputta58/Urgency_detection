import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
import socketio
import uvicorn
import csv

# ---------------------------------------------------
# 1️⃣ ENV + SUPABASE CONFIGURATION
# ---------------------------------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Missing Supabase credentials. Check your .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------
# 2️⃣ FASTAPI SETUP
# ---------------------------------------------------
fastapi_app = FastAPI()

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------------------------------------------
# 3️⃣ SOCKET.IO SETUP
# ---------------------------------------------------
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# ---------------------------------------------------
# 4️⃣ ROUTES
# ---------------------------------------------------
# API endpoint to fetch all messages for agent dashboard
@fastapi_app.get("/api/messages")
async def get_messages():
    response = supabase.table("messages").select("*").order("Timestamp (UTC)", desc=False).execute()
    return response.data
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
import socketio
import uvicorn
import csv

# ---------------------------------------------------
# 1️⃣ ENV + SUPABASE CONFIGURATION
# ---------------------------------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Missing Supabase credentials. Check your .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------
# 2️⃣ FASTAPI SETUP
# ---------------------------------------------------
fastapi_app = FastAPI()

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------------------------------------------
# 3️⃣ SOCKET.IO SETUP
# ---------------------------------------------------
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# ---------------------------------------------------
# 4️⃣ ROUTES
# ---------------------------------------------------
@fastapi_app.get("/", response_class=HTMLResponse)
async def get_user_portal(request: Request):
    """Render user dashboard."""
    return templates.TemplateResponse("customer_form.html", {"request": request})
# Add agent dashboard route
@fastapi_app.get("/agent", response_class=HTMLResponse)
async def get_agent_portal(request: Request):
    try:
        response = supabase.table("messages").select("*").execute()
        messages = response.data
    except Exception as e:
        messages = []
        print("Error fetching messages:", e)
    return templates.TemplateResponse("agent.html", {"request": request, "messages": messages})

# Urgency detection helper
def is_urgent(message_text):
    urgent_keywords = [
        "loan", "approval", "disburse", "rejected", "clearance", "CRB", "salary", "urgent", "review", "denied"
    ]
    text = message_text.lower()
    return any(word in text for word in urgent_keywords)

@fastapi_app.get("/", response_class=HTMLResponse)
async def get_agent_portal(request: Request):
    """Render agent portal with messages from Supabase, marking urgent ones."""
    try:
        response = supabase.table("messages").select("*").execute()
        messages = response.data
        # Add urgency flag to each message
        for msg in messages:
            msg["urgent"] = is_urgent(msg.get("message", ""))
    except Exception as e:
        messages = []
        print("Error fetching messages:", e)

    return templates.TemplateResponse(
        "agent.html", {"request": request, "messages": messages}
    )


# CSV Import Route
@fastapi_app.post("/import_csv")
async def import_csv():
    """Import messages from CSV file into Supabase."""
    csv_path = os.path.join(os.path.dirname(__file__), "GeneralistRails_Project_MessageData - GeneralistRails_Project_MessageData.csv")
    imported = 0
    errors = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                msg = {
                    "user_id": row.get("User ID"),
                    "timestamp": row.get("Timestamp (UTC"),
                    "body": row.get("Message Body")
                }
                try:
                    supabase.table("messages").insert(msg).execute()
                    imported += 1
                except Exception as e:
                    errors.append(str(e))
        return {"imported": imported, "errors": errors}
    except Exception as e:
        return {"error": str(e)}



# Canned response selection logic
def select_canned_response(message):
    text = message.lower()
    if "loan" in text or "approval" in text or "review" in text:
        return "Your loan application is currently under review."
    if "phone number" in text or "verify" in text:
        return "Please provide your registered phone number for verification."
    return "Thank you for contacting us! We’ll get back to you shortly."

@fastapi_app.post("/send_message")
async def send_message(sender: str = Form(None), text: str = Form(None)):
    """Send new message to Supabase, auto-reply with canned response, and broadcast via Socket.IO."""
    try:
        # Accept both user and agent messages
        if sender and text:
            new_msg = {"sender": sender, "text": text}
            response = supabase.table("messages").insert(new_msg).execute()
            canned_reply = select_canned_response(text)
            reply_msg = {"sender": "AgentBot", "text": canned_reply}
            supabase.table("messages").insert(reply_msg).execute()
            await sio.emit("new_message", new_msg)
            await sio.emit("new_message", reply_msg)
            return JSONResponse(content={"status": "success", "data": response.data, "auto_reply": canned_reply})
        return JSONResponse(content={"status": "error", "message": "Missing sender or text"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)})


@fastapi_app.get("/canned_messages")
async def get_canned_messages():
    """Predefined canned messages for agents."""
    canned = [
        {"id": 1, "text": "Thank you for contacting us! We’ll get back to you shortly."},
        {"id": 2, "text": "Your loan application is currently under review."},
        {"id": 3, "text": "Please provide your registered phone number for verification."},
    ]
    return {"canned_messages": canned}


# ---------------------------------------------------
# 5️⃣ SOCKET.IO EVENTS
# ---------------------------------------------------
@sio.event
async def connect(sid, environ):
    print(f"🔗 Agent connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"❌ Agent disconnected: {sid}")

# ---------------------------------------------------
# 6️⃣ RUN SERVER
# ---------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
