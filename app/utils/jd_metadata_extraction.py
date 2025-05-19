import json
import logging
import asyncio
import google.generativeai as genai
from langchain.output_parsers import (
    ResponseSchema,
    StructuredOutputParser,
    OutputFixingParser,
)
from langchain.prompts import ChatPromptTemplate
from app.core.config import Config

# Configure Gemini API key
genai.configure(api_key=Config.GOOGLE_API_KEY)

logger = logging.getLogger(__name__)

# ─── 1) Define top-level schemas ───────────────────────────────────────────────
job_title_schema = ResponseSchema(
    name="job_title",
    description="Job title extracted from the JD, e.g., Backend Engineer."
)

skills_schema = ResponseSchema(
    name="skills",
    description=(
        "List of up to 10 skill objects. Each object must have keys:\n"
        "  • skill   (string)\n"
        "  • weight  (integer from 1 to 10)\n"
        "  • evidence(string quote or bullet from the JD)\n"
    )
)

# ─── 2) LLM factory ─────────────────────────────────────────────────────────────
def get_llm():
    return genai.GenerativeModel("gemini-2.0-flash")

# ─── 3) Extraction function ────────────────────────────────────────────────────
async def extract_jd_metadata_llm(jd_text: str) -> dict:
    # --- 3.1 Pre-validate length to catch trivial inputs fast ---
    if len(jd_text.strip().split()) < 30:
        raise ValueError("Job description is too short or invalid for extraction.")

    # --- 3.2 Build the parser expecting exactly two keys at top level ---
    parser = StructuredOutputParser(
        response_schemas=[job_title_schema, skills_schema]
    )


    # --- 3.3 A rock-solid SYSTEM prompt that forbids any other shape ---
    SYSTEM = """
You are an expert résumé-engineering agent.

RETURN exactly one JSON OBJECT with two keys:
  • job_title : string
  • skills    : array of objects, each with keys "skill","weight","evidence"

Do NOT return:
  • any top-level arrays
  • markdown, commentary, or extra fields
  • anything other than valid JSON

OTHER RULES:
- Max 10 skills; merge synonyms; sort by weight descending, then A–Z.
- Weights: 10=core/expert (≥3×), 8–9=strong/extensive (≥2×),
           5–7=responsibilities/qualifications once, 1–4=nice-to-have.
""".strip()

    USER = "{job_description}"

    # --- 3.4 Build messages via LangChain (kept for consistency) ---
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM),
        ("human", USER)
    ])
    messages = prompt.format_messages(job_description=jd_text)

    # --- 3.5 Call Gemini synchronously in a thread ---
    def _sync_call():
        # Gemini expects a list of plain strings: [system, user]
        return get_llm().generate_content(
            [SYSTEM, jd_text],
            generation_config={"temperature": 0}
        ).text
        

    raw = await asyncio.to_thread(_sync_call)
    logger.debug(f"LLM raw response:\n{raw}")

    # --- 3.6 Parse and validate JSON output ---
    try:
        parsed = parser.parse(raw)
    except Exception as e:
        logger.error("Failed to parse LLM output. Raw content was:\n%s", raw)
        raise ValueError(f"Output parsing error: {e}")

    # --- 3.7 Handle in-prompt errors ---
    if isinstance(parsed, dict) and parsed.get("error"):
        raise ValueError(parsed["error"])

    # --- 3.8 Coerce `skills` from JSON string to Python list if needed ---
    skills_val = parsed["skills"]
    if isinstance(skills_val, str):
        parsed["skills"] = json.loads(skills_val)

    return parsed
