from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from app.core.config import Config

def get_llm_model():
    """
    Returns a zero-temperature LLM instance (Ollama or OpenAI).
    """
    return ChatOpenAI(
        temperature=0,
        model_name="ollama/llama3",        # or your preferred model
        openai_api_base=Config.OLLAMA_API_BASE
    )

# precise JSON-only extraction prompt
EXTRACTION_PROMPT = """
You are a résumé-engineering agent.  
Your task is to read a raw job-description (JD) and output a single, valid JSON object
that follows exactly the schema below—no extra keys, no commentary.

––––– JSON SCHEMA –––––
{
  "job_title": string,
  "skills": [                                   
    {
      "skill": string,
      "weight": integer,
      "evidence": string
    }
  ]
}
––––– WEIGHTING GUIDELINES –––––
10 = labelled “required”, “core”, “expert”, OR appears ≥3 times  
8-9 = appears ≥2 times OR described as “strong”, “extensive”, “hands-on”  
5-7 = appears once in “Responsibilities” or “Qualifications” sections  
1-4 = appears only in “Nice to have”, “Preferred”, or company boiler-plate  
(Max 30 total skills. Combine obvious synonyms: “Python 3” + “Python” ⇒ “Python”.)

––––– OUTPUT RULES –––––
* Return JSON ONLY—no markdown, no explanations.  
* Preserve valid UTF-8.  
* Do not add or remove keys from the schema.  
* If a section is missing, still include the key with an empty (string or empty array) value.  
* The order of the skills array should be descending by weight, then A-Z.

––––– INPUT –––––
{job_description}
"""

async def extract_jd_metadata_llm(jd_text: str) -> dict:
    """
    Calls the LLM with our strict prompt and returns the parsed JSON.
    """
    llm = get_llm_model()
    prompt = ChatPromptTemplate.from_template(EXTRACTION_PROMPT)
    messages = prompt.format_messages(job_description=jd_text)

    response = await llm.ainvoke(messages)
    raw = response.content.strip()

    try:
        # assume trusted internal JSON; otherwise use json.loads()
        return eval(raw)
    except Exception as e:
        print(f"[❌] Failed to parse JSON from LLM: {e}\nRAW:\n{raw}")
        return {}
