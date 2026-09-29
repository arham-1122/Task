"""Tests for application orchestration and decision engine."""

import sys
from pathlib import Path
import unittest
from unittest.mock import patch

_src_path = str(Path(__file__).resolve().parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from freight_processor.engine import process_freight_document
from freight_processor.extractor import ExtractionError
from freight_processor.models import (
    ExtractedFreightData,
    IssueSeverity,
    Location,
    ProcessingResult,
    ProcessingStatus,
)


class TestEngine(unittest.TestCase):
    """Unit tests for pipeline orchestrator and decision logic."""

    @patch("freight_processor.engine.extract_freight_data")
    def test_approved_document(self, mock_extract):
        """When extraction succeeds and validation has zero issues, document is APPROVED."""
        valid_data = ExtractedFreightData(
            carrier_name="Apex Logistics Solutions LLC",
            load_number="LD-994821",
            pickup_location=Location(city="Dallas", state="TX", zip="75201"),
            delivery_location=Location(city="Atlanta", state="GA", zip="30303"),
            total_linehaul_rate=2200.0,
            fuel_surcharge=350.0,
            total_pay=2550.0,  # 2200 + 350 == 2550
            weight_lbs=42000,   # <= 45000
        )
        mock_extract.return_value = valid_data

        raw_text = "Carrier: Apex Logistics..."
        result: ProcessingResult = process_freight_document(raw_text)

        self.assertEqual(result.status, ProcessingStatus.APPROVED)
        self.assertIsNotNone(result.extracted_data)
        self.assertEqual(result.extracted_data.carrier_name, "Apex Logistics Solutions LLC")
        self.assertEqual(len(result.issues), 0)

    @patch("freight_processor.engine.extract_freight_data")
    def test_flagged_document_with_sample_values(self, mock_extract):
        """When validation encounters issues, document is FLAGGED_FOR_HUMAN_REVIEW and values are preserved."""
        sample_data = ExtractedFreightData(
            carrier_name="Apex Logistics Solutions LLC",
            load_number="LD-994821",
            pickup_location=Location(city="Dallas", state="TX", zip="75201"),
            delivery_location=Location(city="Atlanta", state="GA", zip="30303"),
            total_linehaul_rate=2200.0,
            fuel_surcharge=350.0,
            total_pay=2800.0,  # Math mismatch
            weight_lbs=46800,   # Overweight
        )
        mock_extract.return_value = sample_data

        raw_text = "Carrier: Apex Logistics..."
        result: ProcessingResult = process_freight_document(raw_text)

        self.assertEqual(result.status, ProcessingStatus.FLAGGED_FOR_HUMAN_REVIEW)
        self.assertIsNotNone(result.extracted_data)

        # Verify exact preservation of extracted values without auto-correction
        self.assertEqual(result.extracted_data.total_linehaul_rate, 2200.0)
        self.assertEqual(result.extracted_data.fuel_surcharge, 350.0)
        self.assertEqual(result.extracted_data.total_pay, 2800.0)
        self.assertEqual(result.extracted_data.weight_lbs, 46800)

        # Verify validation issues
        issue_codes = {issue.code for issue in result.issues}
        self.assertEqual(issue_codes, {"RATE_MISMATCH", "OVERWEIGHT_LOAD"})

    @patch("freight_processor.engine.extract_freight_data")
    def test_extraction_failure_handled_gracefully(self, mock_extract):
        """Extraction failures must result in FLAGGED_FOR_HUMAN_REVIEW with EXTRACTION_ERROR issue."""
        mock_extract.side_effect = ExtractionError("Gemini API 500: Server Error")

        raw_text = "Corrupt / unparseable content"
        result: ProcessingResult = process_freight_document(raw_text)

        self.assertEqual(result.status, ProcessingStatus.FLAGGED_FOR_HUMAN_REVIEW)
        self.assertIsNone(result.extracted_data)
        self.assertEqual(len(result.issues), 1)

        issue = result.issues[0]
        self.assertEqual(issue.code, "EXTRACTION_ERROR")
        self.assertEqual(issue.severity, IssueSeverity.ERROR)
        self.assertIn("Gemini API 500", issue.message)

    @patch("freight_processor.engine.extract_freight_data")
    def test_empty_input_handled_gracefully(self, mock_extract):
        """Empty input raising ValueError must result in FLAGGED_FOR_HUMAN_REVIEW without crashing."""
        mock_extract.side_effect = ValueError("raw_text cannot be empty")

        result: ProcessingResult = process_freight_document("")

        self.assertEqual(result.status, ProcessingStatus.FLAGGED_FOR_HUMAN_REVIEW)
        self.assertIsNone(result.extracted_data)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].code, "EXTRACTION_ERROR")


if __name__ == "__main__":
    unittest.main()
