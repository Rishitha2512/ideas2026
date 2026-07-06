"""
llm_analyser.py
----------------

LLM-based analysis engine for earnings call transcripts.

Pipeline:
PDF -> Text -> Claude -> Structured JSON -> Validation

Used by:
    main.py
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any


import config
# -------------------------------------------------------
# Logger
# -------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)
# -------------------------------------------------------
# Claude Client
# -------------------------------------------------------

# -------------------------------------------------------
# Claude Configuration
# -------------------------------------------------------

from openai import OpenAI

client = OpenAI(api_key=config.OPENAI_API_KEY)

MODEL_NAME = config.OPENAI_MODEL
MAX_OUTPUT_TOKENS = config.MAX_OUTPUT_TOKENS
TEMPERATURE = config.TEMPERATURE
# -------------------------------------------------------
# Default Structures
# -------------------------------------------------------

DEFAULT_QUARTER = {
    "quarter": "",
    "summary": "",
    "earnings_triggers": [],
    "business_changes": [],
    "risks_and_issues": [],
    "commitments_made": [],
    "management_tone": {
        "overall": "neutral",
        "score": 5,
        "reasoning": "",
        "key_phrases": []
    },
    "key_metrics_mentioned": {},
}
DEFAULT_CROSS = {
    "deviations": [],
    "narrative_shifts": [],
    "recurring_themes": [],
    "management_credibility_score": 5,
    "credibility_reasoning": "",
    "overall_trend": "stable",
    "analyst_view": "",
}
# -------------------------------------------------------
# JSON Parser
# -------------------------------------------------------

def parse_json_response(text: str) -> dict:
    """
    Extract JSON from Claude response safely.
    """

    text = text.strip()

    text = re.sub(
        r"^```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```",
        "",
        text
    )

    text = text.replace("```", "").strip()

    try:
        return json.loads(text)

    except Exception:

        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )

        if match:

            return json.loads(match.group())

        raise ValueError("Claude did not return valid JSON.")
    
# -------------------------------------------------------
# Prompt Builders
# -------------------------------------------------------

def build_quarter_prompt(
    company_name: str,
    quarter: str,
    transcript: str,
) -> str:
    """
    Prompt for analysing a single earnings call.
    """

    return f"""
You are a senior equity research analyst.

Analyse the following earnings call transcript.

Company:
{company_name}

Quarter:
{quarter}

Return ONLY valid JSON.

Required JSON schema:

{{
  "quarter": "{quarter}",
  "summary": "",
  "earnings_triggers": [
    {{
      "trigger": "",
      "detail": "",
      "confidence": "high"
    }}
  ],
  "business_changes": [
    {{
      "change_type": "",
      "description": "",
      "significance": "major"
    }}
  ],
  "risks_and_issues": [
    {{
      "risk": "",
      "detail": "",
      "category": "",
      "severity": "medium"
    }}
  ],
  "commitments_made": [
    {{
      "commitment": "",
      "metric": "",
      "timeframe": ""
    }}
  ],
  "management_tone": {{
      "overall": "positive",
      "score": 8,
      "reasoning": "",
      "key_phrases": []
  }},
  "key_metrics_mentioned": {{
      "revenue_growth": "",
      "margin": "",
      "order_book": "",
      "guidance": ""
  }}
}}

Rules:

- Output JSON only.
- No markdown.
- No explanation.
- Do not invent numbers.
- If something is unavailable, use an empty string or empty list.

Transcript:

{transcript}
"""
def build_cross_quarter_prompt(
    company_name: str,
    quarterly_results: list[dict],
) -> str:
    """
    Compare all analysed quarters.
    """

    payload = json.dumps(
        quarterly_results,
        indent=2,
        ensure_ascii=False,
    )

    return f"""
You are a senior equity research analyst.

You have already analysed multiple earnings calls.

Compare them.

Company:

{company_name}

Quarter analyses:

{payload}

Return ONLY JSON.

Schema:

{{
    "deviations":[
        {{
            "commitment_quarter":"",
            "commitment":"",
            "check_quarter":"",
            "outcome":"",
            "detail":"",
            "severity":""
        }}
    ],
    "narrative_shifts":[
        {{
            "topic":"",
            "quarters_involved":[],
            "shift_description":""
        }}
    ],
    "recurring_themes":[
        {{
            "theme":"",
            "trend":"",
            "quarters":[]
        }}
    ],
    "management_credibility_score":7,
    "credibility_reasoning":"",
    "overall_trend":"stable",
    "analyst_view":""
}}

Only JSON.

No markdown.

No explanation.
"""

# -------------------------------------------------------
# Validation Functions
# -------------------------------------------------------

def validate_quarter_result(result: dict) -> dict:
    """
    Ensure all required fields exist.
    """

    if not isinstance(result, dict):
        result = {}

    validated = DEFAULT_QUARTER.copy()

    validated.update(result)

    if not isinstance(validated.get("management_tone"), dict):
        validated["management_tone"] = DEFAULT_QUARTER["management_tone"].copy()

    else:
        tone = DEFAULT_QUARTER["management_tone"].copy()
        tone.update(validated["management_tone"])
        validated["management_tone"] = tone

    if not isinstance(validated.get("key_metrics_mentioned"), dict):
        validated["key_metrics_mentioned"] = {}

    for field in (
        "earnings_triggers",
        "business_changes",
        "risks_and_issues",
        "commitments_made",
    ):
        if not isinstance(validated.get(field), list):
            validated[field] = []

    return validated
def validate_cross_quarter(result: dict) -> dict:
    """
    Ensure cross-quarter analysis contains every field.
    """

    if not isinstance(result, dict):
        result = {}

    validated = DEFAULT_CROSS.copy()

    validated.update(result)

    for field in (
        "deviations",
        "narrative_shifts",
        "recurring_themes",
    ):
        if not isinstance(validated.get(field), list):
            validated[field] = []

    if not isinstance(
        validated.get("management_credibility_score"),
        (int, float),
    ):
        validated["management_credibility_score"] = 5

    return validated
# -------------------------------------------------------
# Claude Helper
# -------------------------------------------------------

def call_llm(prompt: str) -> dict:
    """
    Send a prompt to OpenAI and return parsed JSON.
    """

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=TEMPERATURE,
    )

    text = response.choices[0].message.content

    return parse_json_response(text)
# -------------------------------------------------------
# Single Quarter Analysis
# -------------------------------------------------------

def analyse_single_quarter(
    transcript: dict,
    company_name: str,
    verbose: bool = False,
) -> dict:
    """
    Analyse a single earnings-call transcript.

    Parameters
    ----------
    transcript : dict
        Dictionary returned by pdf_extractor.

    company_name : str

    verbose : bool

    Returns
    -------
    dict
    """

    try:

        quarter = transcript.get("quarter", "Unknown")

        transcript_text = transcript.get(
            "text",
            transcript.get("content", "")
        )

        if not transcript_text:

            raise ValueError("Transcript text is empty.")

        if verbose:
            logger.info("Analysing %s ...", quarter)

        prompt = build_quarter_prompt(
            company_name=company_name,
            quarter=quarter,
            transcript=transcript_text,
        )

        result = call_llm(prompt)

        result = validate_quarter_result(result)

        result["quarter"] = quarter

        return result

    except Exception as e:

        logger.exception(e)

        return {
            "quarter": transcript.get("quarter", "Unknown"),
            "summary": "",
            "earnings_triggers": [],
            "business_changes": [],
            "risks_and_issues": [],
            "commitments_made": [],
            "management_tone": {
                "overall": "neutral",
                "score": 5,
                "reasoning": str(e),
                "key_phrases": [],
            },
            "key_metrics_mentioned": {},
            "_error": str(e),
        }
# -------------------------------------------------------
# Cross Quarter Analysis
# -------------------------------------------------------



def analyse_cross_quarters(
    quarterly_results: list[dict],
    company_name: str,
) -> dict:
    """
    Compare all analysed quarters and identify trends.
    """

    logger.info("Running cross-quarter analysis...")

    try:

        prompt = build_cross_quarter_prompt(
            company_name=company_name,
            quarterly_results=quarterly_results,
        )

        result = call_llm(prompt)

        return validate_cross_quarter(result)

    except Exception as e:

        logger.exception(e)

        return {
            "deviations": [],
            "narrative_shifts": [],
            "recurring_themes": [],
            "management_credibility_score": 5,
            "credibility_reasoning": str(e),
            "overall_trend": "stable",
            "analyst_view": "",
            "_error": str(e),
        }


# -------------------------------------------------------
# Complete Pipeline
# -------------------------------------------------------

def run_full_analysis(
    transcripts: list[dict],
    company_name: str,
    verbose: bool = False,
) -> dict:
    """
    Analyse every transcript and perform cross-quarter comparison.

    Parameters
    ----------
    transcripts : list
        Output from pdf_extractor.

    company_name : str

    verbose : bool

    Returns
    -------
    dict
    """

    logger.info(
        "Starting analysis of %d transcript(s)...",
        len(transcripts),
    )

    quarterly_results = []

    for transcript in transcripts:

        result = analyse_single_quarter(
            transcript=transcript,
            company_name=company_name,
            verbose=verbose,
        )

        quarterly_results.append(result)

    deviation_analysis = analyse_cross_quarters(
        quarterly_results=quarterly_results,
        company_name=company_name,
    )

    return {
        "company": company_name,
        "quarters_analysed": len(quarterly_results),
        "quarterly_analyses": quarterly_results,
        "deviation_analysis": deviation_analysis,
    }
