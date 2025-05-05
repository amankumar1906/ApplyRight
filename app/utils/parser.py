import pdfplumber
import os

# --------------- Resume PDF Parsing --------------- #

def parse_resume_pdf(resume_path: str) -> str:
    """
    Extract raw text from a resume PDF using pdfplumber.
    """
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"Resume not found at {resume_path}")

    text = ""
    with pdfplumber.open(resume_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""  # Handle blank pages safely

    return text

# --------------- Job Description Parsing --------------- #

def parse_job_description(jd_path: str) -> str:
    """
    Read the Job Description text file.
    """
    if not os.path.exists(jd_path):
        raise FileNotFoundError(f"Job description not found at {jd_path}")

    with open(jd_path, "r", encoding="utf-8") as file:
        return file.read()
