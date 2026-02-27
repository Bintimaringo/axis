import httpx
import json
import re

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"


def _extract_json(text: str) -> dict:
    """Extract JSON from model output, stripping markdown fences if present."""
    text = text.strip()

    # Direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Last resort: find outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from model output. Raw output:\n{text[:500]}")


async def call_claude(system_prompt: str, user_content: str, model: str, api_key: str) -> dict:
    """Call Claude API with automatic JSON retry on parse failure."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    last_error: Exception | None = None

    for attempt in range(2):
        content = user_content
        if attempt == 1:
            content = (
                user_content
                + "\n\nReturn valid JSON only. No markdown code blocks. No explanation. Just the raw JSON object."
            )

        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": content}],
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(CLAUDE_API_URL, headers=headers, json=payload)
            if not response.is_success:
                try:
                    err_body = response.json()
                    err_msg = err_body.get("error", {}).get("message", response.text)
                except Exception:
                    err_msg = response.text
                raise ValueError(f"Anthropic API error {response.status_code}: {err_msg}")
            data = response.json()
            raw_text = data["content"][0]["text"]

        try:
            return _extract_json(raw_text)
        except (ValueError, json.JSONDecodeError) as e:
            last_error = e
            continue  # retry

    raise ValueError(f"Failed to get valid JSON after retry. Last error: {last_error}")
