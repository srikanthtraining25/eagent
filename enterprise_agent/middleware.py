import re
from typing import Dict, Any

def rai_check(text: str) -> Dict[str, Any]:
    """
    Checks for policy violations (Mock implementation).
    Returns a dict with 'safe': bool and 'reason': str.
    """
    # Mock: Check for "unsafe" keyword
    if "unsafe" in text.lower():
        return {"safe": False, "reason": "Content contains unsafe keywords."}
    return {"safe": True, "reason": ""}

def pii_filter(text: str) -> str:
    """
    Redacts sensitive info (email, phone).
    """
    # Redact Emails
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    text = re.sub(email_pattern, '[EMAIL_REDACTED]', text)
    
    # Redact Phone Numbers (Simple Mock)
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    text = re.sub(phone_pattern, '[PHONE_REDACTED]', text)
    
    return text

def check_permission(user_info: Dict[str, Any], action: str) -> bool:
    """
    Verifies if the user has permission for the action.
    """
    user_role = user_info.get("role", "guest")
    
    if action == "sensitive_action" and user_role != "admin":
        return False
    return True

def post_process_response(response: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filters internal data and updates context based on response.
    """
    # Mock: Filter out internal IDs starting with "INTERNAL_"
    filtered_response = re.sub(r'INTERNAL_\w+', '', response)
    
    updates = {}
    # Mock: Extract submission ID if present
    match = re.search(r'Submission ID: (\d+)', response)
    if match:
        updates["last_submission_id"] = match.group(1)
        
    return {
        "filtered_response": filtered_response,
        "context_updates": updates
    }
