import os
import json
import time
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    jsonify, session, Response, stream_with_context
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager, login_user, login_required, logout_user, current_user, UserMixin
)
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, declarative_base
from datetime import datetime
from google import genai
from upload_routes import upload_bp


# load .env
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///chatbot.db")

if not API_KEY:
    raise EnvironmentError("Please set GOOGLE_API_KEY in environment or .env")

# Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = SECRET_KEY
app.register_blueprint(upload_bp)


# DB setup (SQLAlchemy core)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
db_session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

# Login manager
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

# Models
class User(Base, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(300), nullable=False)
    display_name = Column(String(200), default="User")
    theme = Column(String(20), default="dark")  # default to dark theme
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(300), default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    role = Column(String(20))  # 'user' or 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    chat = relationship("Chat", back_populates="messages")

Base.metadata.create_all(bind=engine)

# Gemini client
client = genai.Client(api_key=API_KEY)

# User loader for flask-login
@login_manager.user_loader
def load_user(user_id):
    try:
        return db_session.get(User, int(user_id))
    except Exception:
        return None

# ---------- Authentication routes ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        pw = request.form.get("password") or ""
        name = request.form.get("display_name") or (email.split("@")[0] if email else "User")
        if not email or not pw:
            flash("Email and password required", "danger")
            return redirect(url_for("register"))
        existing = db_session.query(User).filter_by(email=email).first()
        if existing:
            flash("Email already exists", "warning")
            return redirect(url_for("register"))
        user = User(email=email, password_hash=generate_password_hash(pw), display_name=name)
        db_session.add(user)
        db_session.commit()
        login_user(user)
        return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        pw = request.form.get("password") or ""
        user = db_session.query(User).filter_by(email=email).first()
        if not user or not user.check_password(pw):
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))
        login_user(user)
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ---------- Main UI ----------
@app.route("/")
@login_required
def index():
    chats = db_session.query(Chat).filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).all()
    return render_template("index.html", chats=chats, user=current_user)

# ---------- Chat management ----------
@app.route("/chats", methods=["POST"])
@login_required
def create_chat():
    title = (request.json.get("title") or "New Chat") if request.is_json else (request.form.get("title") or "New Chat")
    chat = Chat(user_id=current_user.id, title=title)
    db_session.add(chat)
    db_session.commit()
    return jsonify({"ok": True, "chat_id": chat.id, "title": chat.title})

@app.route("/chats/<int:chat_id>/rename", methods=["POST"])
@login_required
def rename_chat(chat_id):
    chat = db_session.query(Chat).filter_by(id=chat_id, user_id=current_user.id).first()
    if chat is None:
        return jsonify({"error": "Chat not found"}), 404
    payload = request.get_json() or {}
    title = payload.get("title", "").strip() or chat.title
    chat.title = title
    db_session.commit()
    return jsonify({"ok": True, "title": chat.title})

@app.route("/chats/<int:chat_id>", methods=["DELETE"])
@login_required
def delete_chat(chat_id):
    chat = db_session.query(Chat).filter_by(id=chat_id, user_id=current_user.id).first()
    if chat is None:
        return jsonify({"error": "Chat not found"}), 404
    db_session.delete(chat)
    db_session.commit()
    return jsonify({"ok": True})

@app.route("/chats/<int:chat_id>/messages", methods=["GET"])
@login_required
def get_messages(chat_id):
    chat = db_session.query(Chat).filter_by(id=chat_id, user_id=current_user.id).first()
    if chat is None:
        return jsonify({"error": "Chat not found"}), 404
    msgs = [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in chat.messages
    ]
    return jsonify({"messages": msgs, "title": chat.title})

# ---------- Static chat endpoint (fallback) ----------
@app.route("/chats/<int:chat_id>/chat", methods=["POST"])
@login_required
def chat_static(chat_id):
    payload = request.get_json() or {}
    text = (payload.get("message") or "").strip()
    if not text:
        return jsonify({"error": "Empty message"}), 400

    chat = db_session.query(Chat).filter_by(id=chat_id, user_id=current_user.id).first()
    if chat is None:
        return jsonify({"error": "Chat not found"}), 404

    # save user message
    user_msg = Message(chat_id=chat.id, role="user", content=text)
    db_session.add(user_msg)
    db_session.commit()

    # Build simple conversation context
    msgs = db_session.query(Message).filter_by(chat_id=chat.id).order_by(Message.created_at).all()
    system_prompt = "You are a helpful assistant. Keep responses concise and friendly. Use markdown when appropriate."

    convo = [f"System: {system_prompt}", ""]
    for m in msgs:
        role = "User" if m.role == "user" else "Assistant"
        convo.append(f"{role}: {m.content}")
    prompt_text = "\n".join(convo)

    try:
        api_chat = client.chats.create(model=MODEL)
        response = api_chat.send_message(prompt_text)
        bot_text = getattr(response, "text", None)
        if not bot_text:
            outputs = getattr(response, "output", None)
            if outputs and len(outputs) > 0:
                bot_text = str(getattr(outputs[0], "content", outputs[0]))
        if not bot_text:
            bot_text = "Sorry, couldn't generate a reply."
    except Exception as e:
        bot_text = "Error from model: " + str(e)

    assistant_msg = Message(chat_id=chat.id, role="assistant", content=bot_text)
    db_session.add(assistant_msg)
    db_session.commit()

    return jsonify({"reply": bot_text})

# ---------- Streaming SSE endpoint (emulated chunking if no native streaming) ----------
@app.route("/chats/<int:chat_id>/send", methods=["POST"])
@login_required
def send_message(chat_id):
    payload = request.get_json() or {}
    text = (payload.get("message") or "").strip()
    if not text:
        return jsonify({"error": "Empty message"}), 400

    chat = db_session.query(Chat).filter_by(id=chat_id, user_id=current_user.id).first()
    if chat is None:
        return jsonify({"error": "Chat not found"}), 404

    # save user message
    user_msg = Message(chat_id=chat.id, role="user", content=text)
    db_session.add(user_msg)
    db_session.commit()

    # build prompt context
    msgs = db_session.query(Message).filter_by(chat_id=chat.id).order_by(Message.created_at).all()
    system_prompt = "You are a helpful assistant. Keep responses concise and use markdown."

    convo = [f"System: {system_prompt}", ""]
    for m in msgs:
        role = "User" if m.role == "user" else "Assistant"
        convo.append(f"{role}: {m.content}")
    prompt_text = "\n".join(convo)

    def generator():
        try:
            api_chat = client.chats.create(model=MODEL)
            # Try typical (non-streaming) call first; many genai clients do not expose token streaming in Python for all models.
            response = api_chat.send_message(prompt_text)

            # extract full text
            full_text = getattr(response, "text", None)
            if not full_text:
                outputs = getattr(response, "output", None)
                if outputs and len(outputs) > 0:
                    full_text = str(getattr(outputs[0], "content", outputs[0]))
            if not full_text:
                full_text = "Sorry, couldn't generate a reply."

            # Emulate streaming: yield small chunks as SSE events
            for i in range(0, len(full_text), 80):
                chunk = full_text[i:i+80]
                ev = f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield ev
                time.sleep(0.03)  # tweak the feel
            # final event
            yield f"data: {json.dumps({'done': True, 'full': full_text})}\n\n"

            # persist assistant message
            assistant_msg = Message(chat_id=chat.id, role="assistant", content=full_text)
            db_session.add(assistant_msg)
            db_session.commit()

        except Exception as e:
            # notify frontend to fallback silently
            yield "event: stream_error\ndata: fallback\n\n"

    return Response(stream_with_context(generator()), mimetype="text/event-stream")

# ---------- Profile ----------
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = (request.form.get("display_name") or "").strip() or current_user.display_name
        theme = request.form.get("theme") or current_user.theme
        user = db_session.get(User, current_user.id)
        if user:
            user.display_name = name
            user.theme = theme
            db_session.commit()
            flash("Profile updated", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=current_user)

# ---------- Simple API to get current user ----------
@app.route("/api/me")
@login_required
def me():
    return jsonify({
        "id": current_user.id,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "theme": current_user.theme
    })

# ---------- Clean shutdown / teardown ----------
@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

if __name__ == "__main__":
    # debug mode for local dev; set debug=False in production
    app.run(debug=True, port=5000)
