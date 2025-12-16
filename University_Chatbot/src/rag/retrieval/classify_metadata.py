
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
import json
import logging
from core.llm import get_llm
import re
# === Setup Logging ===
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

llm = get_llm()

def fix_apostrophes(text: str) -> str:
    """
    Replace standard apostrophes with typographic ones for consistency.
    """
    return text.replace("'", "’")

# === Predefined Header Categories ===
RAW_HEADERS = [
    "École Supérieure d'Ingénieurs de Beyrouth (ESIB)",
    "Département des Classes Préparatoires",
    "Département Génie Électrique et Mécanique",
    "Département Génie Civil et Environnement",
    "Département Génie Chimique et Pétrochimique",
    "Département des Etudes Doctorales",
    "CINET : Centre des Industries Électriques et des Télécommunications (NUD)",
    "CLERC : Centre Libanais d'Etudes et de Recherches de la Construction"
]
HEADERS = [fix_apostrophes(h) for h in RAW_HEADERS]

# === Cached Static Prompt Body ===
STATIC_PROMPT_BODY = f"""
You are an expert classifier for the engineering school (ESIB) at Saint Joseph University in Beirut (USJ).

Your tasks:
1. First, generate a short, descriptive header that summarizes the topic of this query.
2. Then, based on the classification rules, select the most relevant predefined header from the list below.

=== Classification Rules ===
1. École Supérieure d'Ingénieurs de Beyrouth (ESIB): Choose if the query is administrative or general (general questions about the program)— related to history, mission, vision, admissions (first year , including for master's/PhD), requirements, language or study language of a program,tuition, directors, student life, or overall school services — but not about specific departmental courses or academic content.ALWAYS admission and application requirements regardless of department.
2. Département des Classes Préparatoires: Choose if the query is specifically about preparatory classes or courses—such as the Programme Préparatoire or Programme Concours (the first two years of the engineering school), the preparatory curriculum structure, or competitive admission preparation for French Grandes Écoles, even if the question mentions a specific engineering track or department.
3. Département Génie Électrique et Mécanique: Choose only if the query is about undergraduate electrical or mechanical or information and communications or computer programs, courses, or projects — and not about graduate/master/Ph.D. programs.
4. Département Génie Civil et Environnement: Choose if the query is related to civil engineering, environmental engineering, construction, or sustainability programs whether it is credits,courses,..
5. Département Génie Chimique et Pétrochimique: Choose if the query pertains to chemical or petrochemical engineering, including industrial processes, chemistry, and refining.
6. Département des Etudes Doctorales: Choose if the query is related to academic information (not administrative) about any master's or doctoral program (including "Master en ..." or Ph.D. programs), research opportunities, thesis topics — even if the query also mentions a specific engineering department.If the user wants to know general information about a masters degree.Do NOT choose this if the query is administrative or general — such as asking what master's programs exist, how to apply, admission requirements, or tuition — in those cases choose "École Supérieure d’Ingénieurs de Beyrouth (ESIB)".example:Tell me about master's in ..
7. CINET : Centre des Industries Électriques et des Télécommunications (NUD): Choose if the query concerns research or development in the electrical industry, telecommunications, or related technologies.also called CIMTI Centre d'Informatique, de Modélisation et de Technologies de l'Information (NUD)
8. CLERC : Centre Libanais d'Etudes et de Recherches de la Construction: Choose if the query is about construction research, methods, materials, or innovations in the building industry.

Choose ONLY ONE of the following headers exactly as written:
{chr(10).join([f'- "{h}"' for h in HEADERS])}
If no relevant header exists, return "None".

=== Your Response Format (JSON) ===
{{
  "generated_header": "career services for students",
  "header": "École Supérieure d'Ingénieurs de Beyrouth (ESIB)"
}}

Respond ONLY with the JSON.
"""

def generate_classification_prompt(query: str) -> str:
    return f'{STATIC_PROMPT_BODY}\nQuery: "{query}"'

def classify_query_header(query: str) -> dict:
    prompt = generate_classification_prompt(query)
    logger.debug(f"Prompt sent to Gemini:\n{prompt}")

    try:
        response = llm.generate_content(prompt)
        result_text = response.text.strip()
        logger.debug(f"Response from Gemini:\n{result_text}")

        try:
            parsed = json.loads(result_text)
        except json.JSONDecodeError:

            match = re.search(r'\{.*?\}', result_text, re.DOTALL)
            parsed = json.loads(match.group(0)) if match else {}
        
        header = fix_apostrophes(parsed.get("header", "")).strip()
        if header in HEADERS:
            logger.info(f"Classified header: {header}")
            return {"Header 1": header}
        else:
            logger.warning(f"Returned header not in predefined list: {header}")

    except Exception as e:
        logger.error(f"Error during classification: {e}")

    return {"Header 1": "None"}

if __name__ == "__main__":
    example_query = "What are the specific admission requirements for the Master of Science in Artificial Intelligence (AI) program at the University of Saint Joseph (USJ)?"
    result = classify_query_header(example_query)
    print("Final classification result:", result)
