"""
csv_reporter.py
---------------

Exports analysis results to CSV and JSON.

Functions
---------
generate_csv_report()
generate_json_report()
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _safe_join(items, key=None):
    """
    Join a list into a readable string.

    Examples
    --------
    ["A","B"] -> "A | B"

    [{"risk":"Demand"},
     {"risk":"Margin"}]
        -> "Demand | Margin"
    """

    if not items:
        return ""

    if key is None:
        return " | ".join(str(x) for x in items)

    values = []

    for item in items:
        if isinstance(item, dict):
            values.append(str(item.get(key, "")))
        else:
            values.append(str(item))

    return " | ".join(values)


# ---------------------------------------------------------
# CSV Export
# ---------------------------------------------------------

def generate_csv_report(
    quarterly_analyses: list,
    company_name: str,
    output_path: str | Path,
):
    """
    Export quarterly analysis to CSV.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [

        "Quarter",

        "Summary",

        "Tone",

        "Tone Score",

        "Revenue Growth",

        "Margin",

        "Order Book",

        "Guidance",

        "Earnings Triggers",

        "Business Changes",

        "Risks",

        "Commitments"

    ]

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for q in quarterly_analyses:

            metrics = q.get(
                "key_metrics_mentioned",
                {},
            )

            writer.writerow({

                "Quarter":
                    q.get("quarter", ""),

                "Summary":
                    q.get("summary", ""),

                "Tone":
                    q.get("management_tone", {})
                     .get("overall", ""),

                "Tone Score":
                    q.get("management_tone", {})
                     .get("score", ""),

                "Revenue Growth":
                    metrics.get("revenue_growth", ""),

                "Margin":
                    metrics.get("margin", ""),

                "Order Book":
                    metrics.get("order_book", ""),

                "Guidance":
                    metrics.get("guidance", ""),

                "Earnings Triggers":
                    _safe_join(
                        q.get(
                            "earnings_triggers",
                            []
                        ),
                        "trigger"
                    ),

                "Business Changes":
                    _safe_join(
                        q.get(
                            "business_changes",
                            []
                        ),
                        "description"
                    ),

                "Risks":
                    _safe_join(
                        q.get(
                            "risks_and_issues",
                            []
                        ),
                        "risk"
                    ),

                "Commitments":
                    _safe_join(
                        q.get(
                            "commitments_made",
                            []
                        ),
                        "commitment"
                    )

            })

    return output_path


# ---------------------------------------------------------
# JSON Export
# ---------------------------------------------------------

def generate_json_report(
    quarterly_analyses: list,
    company_name: str,
    output_path: str | Path,
):
    """
    Export JSON report.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {

        "company": company_name,

        "quarters": len(
            quarterly_analyses
        ),

        "analysis": quarterly_analyses,

    }

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False,
        )

    return output_path


# ---------------------------------------------------------
# CLI Test
# ---------------------------------------------------------

if __name__ == "__main__":

    sample = [

        {

            "quarter": "Q3FY25",

            "summary": "Revenue improved.",

            "management_tone": {

                "overall": "positive",

                "score": 8,

            },

            "key_metrics_mentioned": {

                "revenue_growth": "12%",

                "margin": "23%",

                "order_book": "₹40,000 Cr",

                "guidance": "Maintain"

            },

            "earnings_triggers": [

                {

                    "trigger": "AI demand"

                }

            ],

            "business_changes": [

                {

                    "description": "Expanded Europe"

                }

            ],

            "risks_and_issues": [

                {

                    "risk": "Currency"

                }

            ],

            "commitments_made": [

                {

                    "commitment": "Improve margins"

                }

            ]

        }

    ]

    generate_csv_report(
        sample,
        "TEST",
        "sample.csv",
    )

    generate_json_report(
        sample,
        "TEST",
        "sample.json",
    )

    print("Sample files generated.")