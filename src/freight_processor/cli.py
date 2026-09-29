"""Command-line interface entry point for freight document processing."""

import argparse
import sys
from pathlib import Path

from freight_processor.engine import process_freight_document
from freight_processor.models import ProcessingResult, ProcessingStatus


def format_summary(result: ProcessingResult, file_path: str) -> str:
    """Format ProcessingResult into a clean, human-readable terminal report."""
    divider = "=" * 60
    lines = [
        divider,
        "FREIGHT DOCUMENT PROCESSING REPORT",
        divider,
        f"Source File: {file_path}",
        f"Status:      {result.status.value}",
        divider,
    ]

    if result.extracted_data:
        data = result.extracted_data
        lines.extend([
            "EXTRACTED DATA:",
            f"  Carrier:           {data.carrier_name}",
            f"  Load Number:       {data.load_number}",
            f"  Pickup:            {data.pickup_location.city}, {data.pickup_location.state} {data.pickup_location.zip}",
            f"  Delivery:          {data.delivery_location.city}, {data.delivery_location.state} {data.delivery_location.zip}",
            f"  Linehaul Rate:     ${data.total_linehaul_rate:,.2f}",
            f"  Fuel Surcharge:    ${data.fuel_surcharge:,.2f}",
            f"  Total Pay:         ${data.total_pay:,.2f}",
            f"  Weight:            {data.weight_lbs:,} lbs",
            divider,
        ])
    else:
        lines.extend([
            "EXTRACTED DATA:     [Extraction Failed / No Data Available]",
            divider,
        ])

    if result.issues:
        lines.append(f"VALIDATION ISSUES ({len(result.issues)}):")
        for idx, issue in enumerate(result.issues, 1):
            lines.append(f"  {idx}. [{issue.severity.value}] {issue.code}: {issue.message}")
        lines.append(divider)
    else:
        lines.append("VALIDATION ISSUES:  None (All rules passed)")
        lines.append(divider)

    return "\n".join(lines)


def main() -> int:
    """CLI execution entrypoint."""
    parser = argparse.ArgumentParser(
        prog="freight_processor",
        description="Process, extract, and validate freight load documents using LLM extraction and deterministic rules.",
    )
    parser.add_argument(
        "file_path",
        type=str,
        help="Path to the raw text freight document file to process.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON serialization of ProcessingResult instead of formatted summary.",
    )

    args = parser.parse_args()
    target_path = Path(args.file_path)

    if not target_path.exists():
        print(f"Error: File not found: '{args.file_path}'", file=sys.stderr)
        return 1

    if not target_path.is_file():
        print(f"Error: Path is not a file: '{args.file_path}'", file=sys.stderr)
        return 1

    try:
        raw_text = target_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"Error reading file '{args.file_path}': {exc}", file=sys.stderr)
        return 1

    result = process_freight_document(raw_text)

    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        print(format_summary(result, str(target_path)))

    return 0


if __name__ == "__main__":
    sys.exit(main())
