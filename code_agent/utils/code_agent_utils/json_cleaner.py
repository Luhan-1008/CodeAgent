import re
import json
from typing import Optional


def clean_json_string(input_string: str) -> str:
    """
    Clean a string that might contain JSON with markdown or explanatory text.
    Extracts JSON objects (patterns like "{ }") or arrays (patterns like "[ ]").

    Args:
        input_string (str): A string that contains JSON, possibly with markdown formatting or explanatory text around it.

    Returns:
        out (str): A clean JSON string ready to be parsed with json.loads()

    Examples:
        ```
        clean_json_string('json: {"key": "value"}')
        {"key": "value"}
        clean_json_string('Sure! I will... [1, 2, 3]')
        [1, 2, 3]
        ```
    """
    if not input_string:
        return ""

    # Pattern to match JSON objects or arrays
    json_pattern = r"({[\s\S]*}|\[[\s\S]*\])"
    json_matches = re.findall(json_pattern, input_string)

    for match in json_matches:
        try:
            json.loads(match)
            return match
        except json.JSONDecodeError:
            continue

    # If no valid JSON found, return empty string
    return ""


def extract_json(input_string: str) -> Optional[dict | list]:
    """
    Extract and parse JSON from a string that might have markdown or explanatory text.
    Extracts JSON objects (patterns like "{ }") or arrays (patterns like "[ ]").

    Args:
        input_string (str): A string that contains JSON, possibly with markdown formatting or explanatory text around it.

    Returns:
        out (Optional[dict|list]): The parsed JSON as a dictionary or list, or empty dict if parsing fails
    """
    try:
        cleaned = clean_json_string(input_string)
        return json.loads(cleaned) if cleaned else {}
    except json.JSONDecodeError:
        return {}
