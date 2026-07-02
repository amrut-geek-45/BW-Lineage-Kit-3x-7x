import requests
import os
from ztable_lookup import get_ztable_info


# ----------------------------------------
# Claude API caller
# ----------------------------------------

def _call_claude(prompt, max_tokens=1000):
    """Call Claude Sonnet via Anthropic API."""
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
            except Exception:
                pass

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        data = response.json()
        return "".join(
            b.get("text", "") for b in data.get("content", [])
        )
    except Exception as e:
        return f"[ERROR] Claude API call failed: {e}"


# ----------------------------------------
# Complexity explanation (with Z tables)
# ----------------------------------------

def generate_reason(code, complexity, score):

    ztable_details = get_ztable_info(code)

    if ztable_details:
        ztable_text = "\n".join([item["table"] for item in ztable_details])
        ztable_section = f"""

4. Are there any custom Z tables present in the logic?

YES

{ztable_text}

"""
    else:
        ztable_section = """

4. Are there any custom Z tables present in the logic?

NO

No custom Z tables found

"""

    prompt = f"""
You are an SAP BW ABAP expert.

Analyze the following BW routine code.

Complexity Level: {complexity}

Rule Engine Score: {score}

Explain:

1. Why this complexity was assigned
2. Key complexity drivers
3. Migration difficulty

Keep the answer concise.

Code:

{code[:6000]}
"""

    return _call_claude(prompt, max_tokens=800) + ztable_section


# ----------------------------------------
# Functional overview
# ----------------------------------------

def generate_functional_overview(code, transformation_summary=None):

    summary_text = ""
    if transformation_summary is not None:
        try:
            summary_text = transformation_summary.to_string()
        except Exception:
            summary_text = ""

    prompt = f"""
You are an SAP BW Functional Consultant.

Explain this transformation
for non-technical users.

Rules:

- Maximum 5 lines
- Avoid ABAP terms
- Explain in business language
- Mention source and target
- Mention custom tables if available

Transformation metadata:

{summary_text}

Transformation code:

{code[:6000]}
"""

    return _call_claude(prompt, max_tokens=400)
