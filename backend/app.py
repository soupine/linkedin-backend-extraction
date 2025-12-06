from flask import Flask, request, jsonify, send_from_directory
import pdfplumber
import re

from extractor import extract_structured_profile
from feedback import build_profile_feedback
from image_quality import analyze_profile_photo

# --------------------------------------------------------------------
# Flask app: serve frontend + API
# --------------------------------------------------------------------
# static_folder='.' -> sirve index.html, script.js, style.css del mismo directorio
app = Flask(__name__, static_folder='.', static_url_path='')


# ---------------- Frontend route ----------------
@app.route("/")
def index():
    # Sirve el index.html de la misma carpeta donde está app.py
    return send_from_directory('.', 'index.html')


# --------------------------------------------------------------------
# Helper: robust text + photo extractor for PDF/HTML uploads
# --------------------------------------------------------------------
def extract_text_and_photo_from_upload(file_storage):
    """
    Detect if the uploaded file is a real PDF.
    - If it is, use pdfplumber to extract text and the first image.
    - If not, treat it as plain text / HTML and return text only.

    Returns:
        text (str), photo (PIL.Image.Image or None)

    Raises:
        ValueError for invalid/corrupt PDFs or unreadable content.
    """
    # Leer primeros bytes para ver si realmente es un PDF
    head = file_storage.read(5)
    file_storage.seek(0)

    is_pdf = head.startswith(b"%PDF-")

    # -------- CASE A: NO ES PDF REAL (HTML / TXT / otra cosa) --------
    if not is_pdf:
        raw = file_storage.read()
        file_storage.seek(0)

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="ignore")

        # Si parece HTML, limpiar etiquetas básicas
        if "<html" in text.lower():
            text = re.sub(r"<[^>]+>", " ", text)

        return text, None

    # -------------------- CASE B: SÍ ES PDF --------------------------
    text = ""
    first_photo = None

    try:
        with pdfplumber.open(file_storage) as pdf:
            for page in pdf.pages:
                # ---- Texto ----
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"

                # ---- Primera imagen como foto de perfil ----
                if first_photo is None and page.images:
                    img_info = page.images[0]
                    bbox = (
                        img_info["x0"],
                        img_info["top"],
                        img_info["x1"],
                        img_info["bottom"],
                    )
                    try:
                        cropped_page = page.crop(bbox)
                        page_image = cropped_page.to_image(resolution=150)
                        first_photo = page_image.original  # PIL.Image
                    except Exception:
                        first_photo = None
    except Exception as e:
        # Cualquier problema leyendo el PDF -> lo convertimos en error controlado
        raise ValueError("Invalid or unreadable PDF") from e

    file_storage.seek(0)
    return text, first_photo


def extract_text_from_pdf(file_storage):
    """
    Backwards-compatible helper, so other modules can still call this.
    """
    text, _ = extract_text_and_photo_from_upload(file_storage)
    return text


# --------------------------------------------------------------------
# API endpoints
# --------------------------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Extract text + profile photo (PDF or HTML)
    try:
        text, photo = extract_text_and_photo_from_upload(file)
    except ValueError as e:
        # Error controlado: PDF corrupto o no legible
        return jsonify({
            "status": "error",
            "message": "Could not read this file. "
                       "Make sure it is a valid LinkedIn PDF export or HTML file.",
            "details": str(e),
        }), 400

    # Structured profile from extractor
    structured_data = extract_structured_profile(text)

    # NLP feedback
    feedback = build_profile_feedback(structured_data)

    # Image quality feedback (if a photo was found)
    photo_feedback = None
    if photo is not None:
        try:
            photo_feedback = analyze_profile_photo(photo)
        except Exception:
            photo_feedback = None

    return jsonify({
        "status": "success",
        "source": file.filename,
        "profile": structured_data,
        "feedback": feedback,
        "photo_feedback": photo_feedback
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "LinkedIn backend running"})


@app.route("/debug/extract-text", methods=["POST"])
def debug_extract_text():
    """
    Example:
    JSON-Body:
    {
      "text": "Summary ... Experience ... Education ... Skills ..."
    }
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No 'text' provided"}), 400

    profile = extract_structured_profile(text)
    feedback = build_profile_feedback(profile)

    return jsonify({
        "status": "success",
        "profile": profile,
        "feedback": feedback,
    })


if __name__ == "__main__":
    app.run(debug=True)
