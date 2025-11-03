# linkedin-backend-extraction

Flask backend for LinkedIn AI profile evaluator – text extraction prototype





Flask backend for parsing and structuring LinkedIn profile PDFs/HTMLs.



\## Features

\- Extracts PDF text via \*\*pdfplumber\*\*

\- Splits text into sections: Summary, Experience, Education, Skills

\- Applies \*\*AI normalization\*\*:

&nbsp; - Job title normalization (RapidFuzz)

&nbsp; - Skill standardization

&nbsp; - Named Entity Recognition via \*\*spaCy\*\* (`en\_core\_web\_sm`)

\- Returns clean structured JSON profile



\## API Endpoints

| Method | Route                 | Description |

|--------|--------               |-------------|

| `POST` | `/upload`             | Upload a PDF file |

| `POST` | `/debug/extract-text` | Send plain text for AI parsing (testing only) |

| `GET`  | `/health`             | Health-check endpoint |





\## Example JSON Output

```json

{

&nbsp; "status": "success",

&nbsp; "profile": {

&nbsp;   "summary": "Machine Learning Engineer passionate about NLP...",

&nbsp;   "experience": \[

&nbsp;     {

&nbsp;       "title": "Data Scientist",

&nbsp;       "company": "Acme Corp",

&nbsp;       "start\_date": "2018-06",

&nbsp;       "end\_date": "2020-12",

&nbsp;       "location": "Berlin",

&nbsp;       "description": "Worked on predictive analytics"

&nbsp;     }

&nbsp;   ],

&nbsp;   "education": \[

&nbsp;     {"school": "TUM", "degree": "M.Sc.", "field": "CS", "start\_year": "2016", "end\_year": "2018"}

&nbsp;   ],

&nbsp;   "skills": \["Python", "NLP", "spaCy", "PyTorch"]

&nbsp; }

}



