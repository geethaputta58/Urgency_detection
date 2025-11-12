import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
import socketio
import uvicorn

# ENV + SUPABASE CONFIGURATION
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# FASTAPI SETUP
fastapi_app = FastAPI()
fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# SOCKET.IO SETUP
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# ROUTES
@fastapi_app.get("/", response_class=HTMLResponse)
async def get_user_portal(request: Request):
    return templates.TemplateResponse("customer_form.html", {"request": request})


@fastapi_app.post("/send_message")
async def send_message(customer_id: str = Form(...), customer_name: str = Form(...), subject: str = Form(...), body: str = Form(...)):
    msg = {
        "user_id": customer_id,
        "customer_name": customer_name,
        "message": body,
        "subject": subject
    }

    # Hardcoded AI response logic
    def get_ai_response(user_msg):
        text = user_msg.lower()
        if any(word in text for word in ["loan", "approval", "disburse", "urgent", "salary"]):
            return {"message": "Your inquiry is urgent and will be prioritized by our team.", "sender": "AgentBot", "priority": "high"}
        if any(word in text for word in ["feedback", "suggestion"]):
            return {"message": "Thank you for your feedback! We value your input.", "sender": "AgentBot", "priority": "normal"}
        if any(word in text for word in ["help", "support", "human"]):
            return {"message": "A human agent will assist you shortly.", "sender": "AgentBot", "priority": "normal"}
        return {"message": "Thank you for reaching out! We'll get back to you soon.", "sender": "AgentBot", "priority": "normal"}

    ai_msg = get_ai_response(body)
    ai_msg["customer_name"] = customer_name
    supabase.table("messages").insert(ai_msg).execute()
    await sio.emit("new_message", ai_msg)
    return JSONResponse(content={"status": "success", "data": msg, "ai": ai_msg})

# API endpoint to fetch all messages
@fastapi_app.get("/api/messages")
async def get_messages():
    response = supabase.table("messages").select("*").order("Timestamp (UTC)", desc=False).execute()
    return response.data

@sio.event
async def connect(sid, environ):
    print(f"🔗 User connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"❌ User disconnected: {sid}")

if __name__ == "__main__":
    uvicorn.run("user_server:app", host="127.0.0.1", port=8001, reload=True)
