import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
import socketio
import uvicorn

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
async def get_agent_portal(request: Request):
    """Render agent portal with messages from Supabase."""
    try:
        response = supabase.table("messages").select("*").execute()
        messages = response.data
    except Exception as e:
        messages = []
        print("Error fetching messages:", e)

    return templates.TemplateResponse(
        "agent.html", {"request": request, "messages": messages}
    )


@fastapi_app.post("/send_message")
async def send_message(sender: str = Form(...), text: str = Form(...)):
    """Send new message to Supabase and broadcast via Socket.IO."""
    try:
        new_msg = {"sender": sender, "text": text}
        response = supabase.table("messages").insert(new_msg).execute()

        # Broadcast in real-time to connected agents
        await sio.emit("new_message", new_msg)

        return JSONResponse(content={"status": "success", "data": response.data})
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
