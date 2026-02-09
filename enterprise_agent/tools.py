from langchain_core.tools import tool
from typing import Dict, Any

# Mock KB Tool
@tool
def search_kb(query: str) -> str:
    """
    Searches the internal knowledge base for policy and procedure information.
    Useful for answering questions about 'how to', 'policy', 'rules', etc.
    """
    print(f"[KB Search] Query: {query}")
    if "leave" in query.lower() or "policy" in query.lower():
        return "Leave Policy: Employees are entitled to 20 days of paid leave per year. Requests must be submitted via the HR portal."
    elif "it" in query.lower() or "support" in query.lower():
        return "IT Support: For password resets, use the portal. For hardware issues, file a ticket."
    else:
        return "No specific policy found for this query in the Knowledge Base."

# Mock Action Tool
@tool
def perform_action(id: str, data: str) -> str:
    """
    Executes a sensitive operation or update on behalf of the user.
    Use this for actions like 'update email', 'reset password', 'submit request', etc.
    The 'id' should be a unique identifier (use '12345' for tests) and 'data' contains details.
    """
    print(f"[Action] Executing with data: id={id}, data={data}")
    return f"Action executed successfully. INTERNAL_ID_999. Submission ID: {id}"
