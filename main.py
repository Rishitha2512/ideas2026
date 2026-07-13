from pathlib import Path
import argparse
import sys

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import OUTPUT_FOLDER, MAX_QUARTERS

import fetcher
import pdf_extractor
import llm_analyser
import html_reporter
import csv_reporter
print("MAIN.PY LOADED")
console = Console()


def build_parser():
    parser = argparse.ArgumentParser(
        description="Concall Analyser"
    )

    parser.add_argument(
    "--company",
    help="Company name, NSE symbol or BSE code"
    )

    

    parser.add_argument(
        "--manual",
        nargs="*",
        help="Manual PDF files"
    )

    parser.add_argument(
        "--output",
        nargs="*",
        default=["html", "csv", "json"],
        choices=["html", "csv", "json"],
        help="Output formats"
    )

    parser.add_argument(
        "--verbose",
        action="store_true"
    )

    return parser


def load_transcripts(args):

    console.print(f"[cyan]Loading company: {args.company}[/cyan]")

    transcripts = pdf_extractor.load_company_pdfs(args.company)

    return transcripts

def save_reports(
    analysis_result,
    company_name,
    output_formats
):
    output_dir = Path(OUTPUT_FOLDER)
    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    safe_name = (
        company_name
        .replace(" ", "_")
        .replace("/", "_")
    )

    if "html" in output_formats:

        html_file = output_dir / f"{safe_name}_report.html"

        html_reporter.generate_html(
            analysis_result,
            company_name,
            html_file
        )

        console.print(
            f"[green]HTML:[/green] {html_file}"
        )

    if "csv" in output_formats:

        csv_file = output_dir / f"{safe_name}_report.csv"

        csv_reporter.generate_csv_report(
            analysis_result["quarterly_analyses"],
            company_name,
            csv_file
        )

        console.print(
            f"[green]CSV:[/green] {csv_file}"
        )

    if "json" in output_formats:

        json_file = output_dir / f"{safe_name}_report.json"

        csv_reporter.generate_json_report(
            analysis_result["quarterly_analyses"],
            company_name,
            json_file
        )

        console.print(
            f"[green]JSON:[/green] {json_file}"
        )


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.company:

        company_name = input(
            "Enter Company Name: "
        ).strip()

        if not company_name:
            console.print(
                "[red]Company name cannot be empty.[/red]"
            )
            sys.exit(1)

        args.company = company_name.upper()

    else:

        args.company = args.company.strip().upper()

    try:

        transcripts = load_transcripts(args)

        if not transcripts:
            console.print(
                "[red]No transcripts available.[/red]"
            )
            sys.exit(1)

        console.print(
            f"[green]Loaded {len(transcripts)} transcript(s)[/green]"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console,
        ) as progress:

            task = progress.add_task(
                "Running LLM analysis...",
                total=None,
            )

            analysis_result = (
                llm_analyser.run_full_analysis(
                    transcripts=transcripts,
                    company_name=args.company,
                    verbose=args.verbose,
                )
            )

            progress.update(
                task,
                completed=True
            )

        save_reports(
            analysis_result,
            args.company,
            args.output
        )

        console.print(
            "\n[bold green]Analysis Complete[/bold green]"
        )

    except Exception as e:

        console.print(
            f"[bold red]Error:[/bold red] {e}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
