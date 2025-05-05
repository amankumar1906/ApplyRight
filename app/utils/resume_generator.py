import json, asyncio, textwrap, google.generativeai as genai
from app.core.config import Config

genai.configure(api_key=Config.GOOGLE_API_KEY)

# ──────────────────────────────────────────────────────────────────────────────
def _generate_tailored_resume_sync(resume_text: str, jd_metadata: dict) -> str:
    """
    Rewrite PROFESSIONAL EXPERIENCE + PROJECTS per weighted-skill rules.
    """
    # ---------- Build skill groups by weight ----------------------------------
    high   = [f'{s["skill"]} ({s["weight"]})' for s in jd_metadata["skills"] if s["weight"] > 8]
    medium = [f'{s["skill"]} ({s["weight"]})' for s in jd_metadata["skills"] if 3 <= s["weight"] <= 8]
    low    = [f'{s["skill"]} ({s["weight"]})' for s in jd_metadata["skills"] if s["weight"] < 3]

    def fmt(lst): return ", ".join(lst) if lst else "—"

    # ---------- SYSTEM PROMPT -------------------------------------------------
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


    USER = f"""
    --- ORIGINAL CONTENT START ---
    {resume_text}
    --- ORIGINAL CONTENT END ---
    """

    model   = genai.GenerativeModel("gemini-2.0-flash")
    reply   = model.generate_content([SYSTEM, USER])
    return reply.text 

# ──────────────────────────────────────────────────────────────────────────────
async def generate_tailored_resume(resume_text: str, jd_metadata: dict) -> str:
    """
    Async wrapper that runs the synchronous Gemini call in a thread.
    """
    return await asyncio.to_thread(_generate_tailored_resume_sync, resume_text, jd_metadata)
