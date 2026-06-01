"""Utility functions for LLM node processing."""

import json


def extract_json_from_llm_response(response_text: str) -> dict:
    """
    Extract JSON object from LLM response that may include markdown code blocks and explanations.

    Handles responses like:
    ```json
    { "key": "value" }
    ```

    **Explanation:** Extra text here...

    Args:
        response_text: Raw text response from LLM

    Returns:
        Parsed JSON as dict

    Raises:
        ValueError: If no valid JSON object found
        json.JSONDecodeError: If JSON is malformed
    """
    content = response_text.strip()

    # Remove markdown code block markers
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]

    # Find the JSON object boundaries (look for opening { and closing })
    json_start = content.find("{")
    if json_start == -1:
        raise ValueError("No JSON object found in response")

    # Find the matching closing brace
    brace_count = 0
    json_end = -1
    for i in range(json_start, len(content)):
        if content[i] == "{":
            brace_count += 1
        elif content[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break

    if json_end == -1:
        raise ValueError("No matching closing brace found")

    json_str = content[json_start:json_end]
    return json.loads(json_str)
