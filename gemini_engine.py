import requests
import os

# ----------------------------------------
# Claude API caller
# ----------------------------------------

def _call_claude(prompt, max_tokens=1000):
    """Call Claude Sonnet via Anthropic API."""
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        # Try streamlit secrets if available
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
# Complexity explanation
# ----------------------------------------

def generate_reason(code, complexity, score):

    prompt = f"""
You are an SAP BW ABAP expert.

Analyze this BW transformation code.

Complexity:
{complexity}

Score:
{score}

Explain:

1. Why complexity was assigned
2. Key complexity drivers
3. Migration difficulty

Keep concise.

Code:

{code[:6000]}
"""
    return _call_claude(prompt, max_tokens=800)


# ----------------------------------------
# Functional overview
# ----------------------------------------

def generate_functional_overview(code):

    prompt = f"""
You are an SAP BW Functional Consultant.

Explain in 3-5 lines:

What this transformation does
in business language.

Code:

{code[:6000]}
"""
    return _call_claude(prompt, max_tokens=400)


# ----------------------------------------
# Z table overview
# ----------------------------------------

def generate_ztable_overview(ztable_details):

    if not ztable_details:
        return ""

    text = ""
    for table in ztable_details:
        text += f"""
Table:
{table["table"]}

Description:
{table["description"]}

Fields:
{table["overview"]}
"""

    prompt = f"""
You are an SAP BW Architect.

Analyze these custom tables.

Determine:

1. Master Data /
Transaction Data /
Lookup Table /
Configuration Table

2. Give 2-3 lines
explaining purpose

3. Mention characteristics

Format:

Table:

Type:

Overview:

Characteristics:

Input:

{text}
"""
    return _call_claude(prompt, max_tokens=800)
