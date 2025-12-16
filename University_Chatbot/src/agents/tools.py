from langchain_core.tools import tool
import sys 
import os
from pydantic import BaseModel
from typing import List, Dict, Optional
from difflib import SequenceMatcher

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from rag.retrieval.retrieval_pipeline import hierarchical_retrieval
from rag.retrieval.description_retrieval import find_courses_by_name_from_file  

class FindCourseInput(BaseModel):
    course_name: str
    department_name: Optional[str] = None
    program_name: Optional[str] = None  

def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

@tool
def retrieve_university_info(query: str) -> str:
    """
    Retrieve university-related information using hierarchical search.

    This tool uses the hierarchical retrieval pipeline to find the most 
    relevant documents or information based on the user's query. It is 
    designed to answer questions about Saint Joseph University (USJ), 
    including programs, courses, admissions, faculty, and other university-specific details.

    Args:
        query (str): The user's question or query about the university.

    Returns:
        str: A concatenated string of the retrieved document contents, 
             providing the most relevant information related to the query.

    Example:
        >>> retrieve_university_info("What are the prerequisites for Algèbre 2?")
        "Algèbre 2 prerequisites: Algèbre 1 (020AL1CI2)..."
    """
    results = hierarchical_retrieval(query)
    return "\n\n".join([doc.page_content for doc in results])

@tool
def find_course_tool(input: FindCourseInput) -> str:
    """
    Search for courses by name across all departments using JSON file.
    Optionally filter by department/program.
    Returns all matches with formatted details.
    """
    JSON_PATH = 'storage/data/course_descriptions/courses_by_department.json'

    # Extract values from Pydantic input
    course_name_str = input.course_name
    department_name_str = input.department_name
    program_name_str = input.program_name

    # Get all matching courses
    results = find_courses_by_name_from_file(
        JSON_PATH,
        course_name_str,
        department_name=department_name_str,
        program_name=program_name_str
    )

    if not results:
        dept_msg = f" in '{department_name_str}'" if department_name_str else ""
        prog_msg = f", program '{program_name_str}'" if program_name_str else ""
        return f"No courses found matching '{course_name_str}'{dept_msg}{prog_msg}."

    # Format all found courses
    output_lines = []
    for res in results:
        department = res["department"]
        course = res["course"]
        lines = [f"Department: {department}"]
        if "program" in res:
            lines.append(f"Program: {res['program']}")
        lines.append("Course details:")
        for key, value in course.items():
            lines.append(f"  {key}: {value}")
        output_lines.append("\n".join(lines))
        output_lines.append("-" * 40)

    return "\n".join(output_lines)
