import json
import logging
from langchain_community.chat_models import ChatOllama
from langchain.output_parsers import (
    ResponseSchema,
    StructuredOutputParser,
    OutputFixingParser,
)
from langchain.prompts import ChatPromptTemplate
from app.core.config import Config

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
    return ChatOllama(
        model="mistral:instruct",
        temperature=0,
        base_url=Config.OLLAMA_API_BASE
    )

# ─── 3) Extraction function ────────────────────────────────────────────────────

async def extract_jd_metadata_llm(jd_text: str) -> dict:
    # --- 3.1 Pre-validate length to catch trivial inputs fast ---
    if len(jd_text.strip().split()) < 30:
        raise ValueError("Job description is too short or invalid for extraction.")

    # --- 3.2 Build the parser expecting exactly two keys at top level ---
    format_instructions = StructuredOutputParser(
        response_schemas=[job_title_schema, skills_schema]
    )
    parser = OutputFixingParser.from_llm(
        parser=format_instructions,
        llm=get_llm()
    )

    # --- 3.3 A rock-solid SYSTEM prompt that forbids any other shape ---
    SYSTEM = f"""
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
"""

    USER = "{job_description}"

    # --- 3.4 Fill in the prompt and call Ollama ---
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM),
        ("human", USER)
    ])
    messages = prompt.format_messages(job_description=jd_text)
    response = await get_llm().ainvoke(messages)

    # --- 3.5 Log raw output for debugging even before parsing ---
    raw = response.content
    logger.debug(f"LLM raw response:\n{raw}")

    # --- 3.6 Try to parse, catch any schema violation to inspect raw output ---
    try:
        parsed = parser.parse(raw)
    except Exception as e:
        logger.error("Failed to parse LLM output. Raw content was:\n%s", raw)
        # re-raise as a ValueError so your Kafka consumer can catch it cleanly
        raise ValueError(f"Output parsing error: {e}")

    # --- 3.7 If the model hit the in-prompt precheck, raise that as an error ---
    if isinstance(parsed, dict) and parsed.get("error"):
        raise ValueError(parsed["error"])

    # --- 3.8 Coerce `skills` from JSON string to Python list if needed ---
    skills_val = parsed["skills"]
    if isinstance(skills_val, str):
        parsed["skills"] = json.loads(skills_val)

    return parsed
