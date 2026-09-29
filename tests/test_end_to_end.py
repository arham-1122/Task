"""Deterministic end-to-end pipeline integration tests with mocked extraction."""

import sys
from pathlib import Path
import unittest
from unittest.mock import patch

_src_path = str(Path(__file__).resolve().parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from freight_processor.engine import process_freight_document
from freight_processor.models import (
    ExtractedFreightData,
    Location,
    ProcessingResult,
    ProcessingStatus,
)


class TestEndToEndPipeline(unittest.TestCase):
    """End-to-end integration tests using the reference sample freight document."""

    @patch("freight_processor.engine.extract_freight_data")
    def test_sample_freight_doc_end_to_end(self, mock_extract):
        """Verify the full pipeline on the sample freight document with mocked LLM extraction."""
        # 1. Load sample document text from disk
        doc_path = Path(__file__).resolve().parent.parent / "data" / "sample_freight_doc.txt"
        self.assertTrue(doc_path.exists(), f"Sample document not found at {doc_path}")
        raw_doc_text = doc_path.read_text(encoding="utf-8")
        self.assertIn("Apex Logistics Solutions LLC", raw_doc_text)

        # 2. Mock extraction layer returning exact stated values without math corrections
        mock_extracted_data = ExtractedFreightData(
            carrier_name="Apex Logistics Solutions LLC",
            load_number="LD-994821",
            pickup_location=Location(city="Dallas", state="TX", zip="75201"),
            delivery_location=Location(city="Atlanta", state="GA", zip="30303"),
            total_linehaul_rate=2200.0,
            fuel_surcharge=350.0,
            total_pay=2800.0,
            weight_lbs=46800,
        )
        mock_extract.return_value = mock_extracted_data

        # 3. Run through the real pipeline (engine + validator)
        result: ProcessingResult = process_freight_document(raw_doc_text)

        # 4. Assert extraction called with raw document text
        mock_extract.assert_called_once_with(raw_text=raw_doc_text, client=None)

        # 5. Assert final disposition
        self.assertEqual(result.status, ProcessingStatus.FLAGGED_FOR_HUMAN_REVIEW)

        # 6. Assert extracted values preserved exactly
        self.assertIsNotNone(result.extracted_data)
        self.assertEqual(result.extracted_data.carrier_name, "Apex Logistics Solutions LLC")
        self.assertEqual(result.extracted_data.load_number, "LD-994821")
        self.assertEqual(result.extracted_data.total_linehaul_rate, 2200.0)
        self.assertEqual(result.extracted_data.fuel_surcharge, 350.0)
        self.assertEqual(result.extracted_data.total_pay, 2800.0)
        self.assertEqual(result.extracted_data.weight_lbs, 46800)

        # 7. Assert required validation issue codes
        issue_codes = [issue.code for issue in result.issues]
        self.assertIn("RATE_MISMATCH", issue_codes)
        self.assertIn("OVERWEIGHT_LOAD", issue_codes)
        self.assertEqual(len(result.issues), 2)


if __name__ == "__main__":
    unittest.main()
