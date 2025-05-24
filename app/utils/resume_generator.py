import textwrap
import asyncio
import logging
from contextlib import closing
import google.generativeai as genai
from app.core.config import Config
from docx import Document
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=Config.GOOGLE_API_KEY)

def _generate_tailored_resume_sync(resume_text: str, jd_metadata: dict, reference_resumes: str = "") -> tuple[str, BytesIO]:
    """
    Synchronously generate a tailored resume and save it as a Word document in a BytesIO buffer.

    Args:
        resume_text (str): The original resume text.
        jd_metadata (dict): Job description metadata with skills and job title.
        reference_resumes (str, optional): Reference resumes for context.

    Returns:
        tuple[str, BytesIO]: Tailored resume text and the Word document buffer.

    Raises:
        ValueError: If input data is invalid or empty.
        Exception: If Gemini API or document creation fails.
    """
    # Validate inputs
    if not resume_text or not jd_metadata:
        logger.error("Resume text or JD metadata is empty")
        raise ValueError("Resume text or JD metadata is empty")

    # Format skills based on weight
    high = [f'{s["skill"]} ({s["weight"]})' for s in jd_metadata["skills"] if s["weight"] > 8]
    medium = [f'{s["skill"]} ({s["weight"]})' for s in jd_metadata["skills"] if 3 <= s["weight"] <= 8]
    low = [f'{s["skill"]} ({s["weight"]})' for s in jd_metadata["skills"] if s["weight"] < 3]
    def fmt(lst): return ", ".join(lst) if lst else "—"

    # Construct prompt
    SYSTEM = textwrap.dedent(f"""
        You are an elite, human-sounding résumé editor.

        ── OUTPUT SCOPE ─────────────
        • Return the entire résumé in this exact section order:

        Name and Address Details
        Education
        Skills (merge original + skills extracted from the job description): Group into exactly three bullet sub-headings using distinct categories (e.g., Front-end, Back-end, DevOps); list all skills in each group on a single line, comma-separated, without bullet points.
        Professional Experience
        Projects
        • Each section header appears once, followed by its content.
        • Include up to two projects. If creating a new project, remove the existing one least aligned with the job description.
        ── PRIORITY SKILLS ──────────
        • High emphasis (≥2 mentions): {fmt(high)}

        • Medium emphasis (≥1 mention): {fmt(medium)}

        • Low emphasis (nice-to-have): {fmt(low)}

        ── EXPERIENCE RULES ─────────

        • Retain all existing bullets; rephrase for clarity/metrics while preserving meaning.
        • If a role lacks a high/medium skill, add one new bullet (20–25 words).
        • All bullets must be human-sounding, metric-driven, and avoid AI filler.

        ── PROJECT RULES ────────────

        Evaluate existing projects against priority skills:
        • No priority skills → delete and create one new project (4 bullets).
        • Some priority skills → keep and refine bullets to include missing skills.
        • All priority skills → polish language and integrate skill keywords naturally.
        New projects must:
        • Be realistic (≤2 years old).
        • Include 3 bullets (18–25 words each).
        • Highlight as many priority skills/technologies as possible.
        Final résumé must have no more than two projects.
        ── STYLE & FORMAT ───────────
        • Use bullets starting with action verbs, followed by metrics/outcomes, in plain text (no Markdown/JSON).

        • Keep total length within ±15% of original, avoiding AI fluff phrases.

        • Self-audit: ensure every high skill appears ≥2×, every medium skill ≥1×.

        Respond ONLY with the final résumé, formatted per the above structure. Do not add commentary, markdown, or extra notes.
    """)
    USER = f"""--- ORIGINAL CONTENT START ---\n{resume_text}\n--- ORIGINAL CONTENT END ---"""
    if reference_resumes.strip():
        USER += f"""\n\n--- REFERENCE RESUMES WITH GUARANTEED HIGH SCORE ---\n{reference_resumes.strip()}\n--- END REFERENCES ---"""

    # Generate tailored resume text
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        reply = model.generate_content([SYSTEM, USER])
        tailored_resume_text = reply.text
        if not tailored_resume_text or tailored_resume_text.isspace():
            logger.error("Generated resume text is empty or invalid")
            raise ValueError("Generated resume text is empty or invalid")
    except Exception as e:
        logger.error(f"Failed to generate tailored resume: {e}")
        raise

    # Create Word document
    buffer = BytesIO()
    try:
        doc = Document()
        # Example: Add basic formatting (can be enhanced based on resume structure)
        doc.add_heading("Tailored Resume", level=1)
        for line in tailored_resume_text.strip().splitlines():
            if line.startswith("## "):
                doc.add_heading(line[3:], level=2)
            else:
                doc.add_paragraph(line, style="ListBullet" if line.startswith("- ") else "Normal")
        doc.save(buffer)
        buffer.seek(0)
    except Exception as e:
        logger.error(f"Error creating Word document: {e}")
        buffer.close()
        raise
    return tailored_resume_text, buffer

async def generate_tailored_resume(resume_text: str, jd_metadata: dict, reference_resumes: str = "") -> tuple[str, BytesIO]:
    """
    Asynchronously generate a tailored resume by running the sync function in a thread.

    Args:
        resume_text (str): The original resume text.
        jd_metadata (dict): Job description metadata.
        reference_resumes (str, optional): Reference resumes for context.

    Returns:
        tuple[str, BytesIO]: Tailored resume text and the Word document buffer.
    """
    return await asyncio.to_thread(
        _generate_tailored_resume_sync,
        resume_text,
        jd_metadata,
        reference_resumes
    )