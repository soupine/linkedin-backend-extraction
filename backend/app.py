from flask import Flask, request, jsonify
import pdfplumber
import re

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

# cut into sections ------------------

def split_sections(text):
    sections = {"summary": "", "experience": [], "education": [], "skills": []}
    
    parts = re.split(r'(Experience|Education|Skills)', text, flags=re.IGNORECASE)
    
    for i in range(1, len(parts), 2):
        section_name = parts[i].lower()
        content = parts[i+1].strip()
        
        if "experience" in section_name:
            sections["experience"].append(content)
        elif "education" in section_name:
            sections["education"].append(content)
        elif "skills" in section_name:
            sections["skills"].extend([s.strip() for s in content.split(",")])
        else:
            sections["summary"] += content + "\n"
    
    return sections

# endpoint ------------------

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    text = extract_text_from_pdf(file)
    structured_data = split_sections(text)
    return jsonify(structured_data)


if __name__ == "__main__":
    app.run(debug=True)
