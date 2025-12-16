
import sys , os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from core.prompts import (
    CREDITS_PROMPT_S1,
    CREDITS_PROMPT
)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from utils.utilities import load_rules_from_file
from functools import lru_cache

@lru_cache(maxsize=32)
def get_credit_rules():
    return load_rules_from_file("storage/data/rules/credit_rules.txt")

credit_rules = get_credit_rules()


def generate_credits_interests_plan(context: dict, llm, interests: str = "") -> dict:
    if "error" in context:
        return context

    username = context["username"]
    gpa = context["gpa"]
    semester = context["semester"]
    user_track = context["track"]
    formatted_courses_credits = context["formatted_courses_credits"]
    
    # Compute remaining credits to reach recommended range
    taken_credits = context["semester_status"]["taken_credits"]
    recommended_range = context["semester_status"]["recommended_range"]

    # Assuming recommended_range is a tuple or list like (min, max)
    remaining_low = max(0, recommended_range[0] - taken_credits)
    remaining_high = max(0, recommended_range[1] - taken_credits)

    remaining_text = f"{remaining_low}–{remaining_high} credits remaining to reach the recommended range."

    # Build summary text
    credits_by_type_text = "\n".join(
        f"- {ctype}: Taken {data['taken']} / Expected {data['expected']}"
        for ctype, data in context["credit_summary"].items()
    )

    credits_status_text = f"""
    ### Current Credit Summary by Type:
    {credits_by_type_text}

    ### Semester Progress Status:
    Taken credits: {taken_credits}
    Remaining to reach range: {remaining_text}
    """.strip()

    # Select proper prompt
    if semester == 1:
        prompt_template = CREDITS_PROMPT_S1
    else:
        prompt_template = CREDITS_PROMPT
    prompt = prompt_template.format(
        username=username,
        gpa=gpa,
        credits_status_text=credits_status_text,
        formatted_courses_credits=formatted_courses_credits,
        interests=interests,
        user_track=user_track or 'None',
        credit_rules = credit_rules
    )


    try:
        response = llm.generate_content(prompt)
        recommendation = response.text.strip() if hasattr(response, "text") and response.text else str(response)
    except Exception as e:
        recommendation = f"Gemini error: {str(e)}"

    return {"prompt": prompt, "recommendation": recommendation}

