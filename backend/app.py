from flask import Flask, request, jsonify
import pdfplumber
import re
from extractor import extract_structured_profile
from feedback import build_profile_feedback
from image_quality import analyze_profile_photo
from PIL import Image

app = Flask(__name__)

# extraction PDF ------------------

def extract_text_and_photo_from_pdf(file):
    """
    Extract plain text and the first embedded image (assumed to be the profile photo)
    from a LinkedIn PDF export.

    Returns:
        text (str), photo (PIL.Image.Image or None)
    """
    text = ""
    first_photo = None

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            # ---- Extract text ----
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"

            # ---- Extract first image as profile photo ----
            if first_photo is None and page.images:
                img_info = page.images[0]
                bbox = (img_info["x0"], img_info["top"], img_info["x1"], img_info["bottom"])
                try:
                    # Crop the page to the image bounding box and render it as a PIL image
                    cropped_page = page.crop(bbox)
                    page_image = cropped_page.to_image(resolution=150)
                    first_photo = page_image.original  # this is a PIL.Image
                except Exception:
                    # If anything goes wrong, we just skip image extraction
                    first_photo = None

    return text, first_photo


def extract_text_from_pdf(file):
    """
    Backwards-compatible helper, so I dont have to change everything
    """
    text, _ = extract_text_and_photo_from_pdf(file)
    return text


# endpoint ------------------

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Extract text + profile photo from the PDF
    text, photo = extract_text_and_photo_from_pdf(file)

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
            # In case anything goes wrong, do not break the whole endpoint
            photo_feedback = None

    return jsonify({
        "status": "success",
        "source": file.filename,
        "profile": structured_data,
        "feedback": feedback,           # NLP feedback (summary/experience/skills)
        "photo_feedback": photo_feedback  # image quality scores or null
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "LinkedIn backend running"})


"""
 --- Test ---
"""
@app.route("/debug/extract-text", methods=["POST"])
def debug_extract_text():
    """
    JSON-Body: { "text": "Summary\nResults-driven Machine Learning Engineer with 4+ years of experience in NLP and Computer Vision.\n\nExperience\nMachine Learning Engineer at OpenAI (Jan 2021 - Present)\nWorking on large-scale natural language processing models using PyTorch and spaCy.\n\nData Scientist at Acme Corp (Jun 2018 - Dec 2020)\nDeveloped predictive analytics solutions and data pipelines using Python and SQL.\n\nEducation\nTechnical University of Munich – M.Sc., Computer Science (2016–2018)\nUniversity of Cologne – B.Sc., Data Science (2013–2016)\n\nSkills\nPython, Machine Learning, Deep Learning, NLP, PyTorch, spaCy, SQL, Docker, AWS"}
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