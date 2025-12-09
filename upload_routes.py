# upload_routes.py
import pytesseract
from PIL import Image
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from models import db_session, Chat, Message
from flask_login import login_required, current_user

ALLOWED = {"pdf", "txt", "png", "jpg", "jpeg"}

upload_bp = Blueprint("upload_bp", __name__)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED

@upload_bp.route("/upload/<int:chat_id>", methods=["POST"])
@login_required
def upload_file(chat_id):
    chat = db_session.query(Chat).filter_by(id=chat_id, user_id=current_user.id).first()
    if chat is None:
        return jsonify({"error": "Chat not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid or unsupported file type"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()

    extracted = ""

    # ---- TXT ----
    if ext == "txt":
        extracted = file.read().decode("utf-8", errors="ignore")

    # ---- PDF ----
    elif ext == "pdf":
        pdf = fitz.open(stream=file.read(), filetype="pdf")
        for page in pdf:
            extracted += page.get_text()

    # ---- IMAGE / OCR ----
    else:
        img = Image.open(file.stream)
        extracted = pytesseract.image_to_string(img)

    if not extracted.strip():
        extracted = "[No readable text]"

    # save message into DB
    new_msg = Message(
        chat_id=chat.id,
        role="assistant",
        content=f"📄 **Extracted File Content:**\n\n{extracted}"
    )
    db_session.add(new_msg)
    db_session.commit()

    return jsonify({"ok": True, "extracted": extracted})
