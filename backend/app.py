from flask import Flask, request, jsonify
import pdfplumber
import re
from extractor import extract_structured_profile

app = Flask(__name__)

# extraction PDF ------------------

def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
    return text

# endpoint ------------------

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    text = extract_text_from_pdf(file)
    structured_data = extract_structured_profile(text)
    return jsonify({
        "status": "success",
        "source": file.filename,
        "profile": structured_data
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
    return jsonify({
        "status": "success",
        "profile": extract_structured_profile(text)
    })



if __name__ == "__main__":
    app.run(debug=True)