"""Tests for Gemini LLM extractor layer with mock completions."""

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

_src_path = str(Path(__file__).resolve().parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from freight_processor.extractor import (
    ExtractionError,
    extract_freight_data,
    get_gemini_client,
)
from freight_processor.models import ExtractedFreightData, Location


class TestExtractor(unittest.TestCase):
    """Unit test suite for LLM extraction layer."""

    def test_empty_raw_text_raises_value_error(self):
        """Empty input string must immediately raise ValueError without calling the API."""
        with self.assertRaises(ValueError):
            extract_freight_data("")

        with self.assertRaises(ValueError):
            extract_freight_data("   \n\t  ")

    def test_missing_api_key_raises_extraction_error(self):
        """Extractor should raise ExtractionError if no API key is configured."""
        with patch("freight_processor.extractor.GEMINI_API_KEY", ""):
            with self.assertRaises(ExtractionError):
                get_gemini_client(api_key="")

    def test_successful_mocked_extraction(self):
        """Valid structured response from Gemini mock must deserialize into ExtractedFreightData."""
        expected_data = ExtractedFreightData(
            carrier_name="Apex Logistics Solutions LLC",
            load_number="LD-994821",
            pickup_location=Location(city="Dallas", state="TX", zip="75201"),
            delivery_location=Location(city="Atlanta", state="GA", zip="30303"),
            total_linehaul_rate=2200.0,
            fuel_surcharge=350.0,
            total_pay=2800.0,
            weight_lbs=46800,
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = expected_data.model_dump_json()
        mock_response.parsed = expected_data
        mock_client.models.generate_content.return_value = mock_response

        raw_doc = "Carrier: Apex Logistics Solutions LLC\nLoad #: LD-994821..."
        result = extract_freight_data(raw_text=raw_doc, client=mock_client)

        self.assertIsInstance(result, ExtractedFreightData)
        self.assertEqual(result.carrier_name, "Apex Logistics Solutions LLC")
        self.assertEqual(result.load_number, "LD-994821")
        self.assertEqual(result.total_linehaul_rate, 2200.0)
        self.assertEqual(result.fuel_surcharge, 350.0)
        self.assertEqual(result.total_pay, 2800.0)
        self.assertEqual(result.weight_lbs, 46800)
        self.assertEqual(result.pickup_location.city, "Dallas")
        self.assertEqual(result.delivery_location.city, "Atlanta")

    def test_gemini_api_network_error_raises_extraction_error(self):
        """API network failure must be wrapped cleanly into an ExtractionError."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("503 Service Unavailable / Connection Timeout")

        raw_doc = "Carrier: Apex Logistics Solutions LLC..."
        with self.assertRaises(ExtractionError):
            extract_freight_data(raw_text=raw_doc, client=mock_client)

    def test_malformed_json_response_raises_extraction_error(self):
        """Unparseable or non-conforming JSON payload must raise ExtractionError."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = None
        mock_response.text = '{"carrier_name": "Apex", "total_linehaul_rate": "invalid_number"}'
        mock_client.models.generate_content.return_value = mock_response

        raw_doc = "Carrier: Apex Logistics Solutions LLC..."
        with self.assertRaises(ExtractionError):
            extract_freight_data(raw_text=raw_doc, client=mock_client)


if __name__ == "__main__":
    unittest.main()
