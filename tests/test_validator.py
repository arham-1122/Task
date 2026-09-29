"""Tests for deterministic business rule validation."""

import pytest
from freight_processor.models import (
    ExtractedFreightData,
    IssueSeverity,
    Location,
)
from freight_processor.validator import validate_freight_data


@pytest.fixture
def valid_freight_data() -> ExtractedFreightData:
    """Fixture providing a standard, fully valid freight record."""
    return ExtractedFreightData(
        carrier_name="Apex Logistics Solutions LLC",
        load_number="LD-994821",
        pickup_location=Location(city="Dallas", state="TX", zip="75201"),
        delivery_location=Location(city="Atlanta", state="GA", zip="30303"),
        total_linehaul_rate=2200.0,
        fuel_surcharge=350.0,
        total_pay=2550.0,  # 2200.0 + 350.0 == 2550.0
        weight_lbs=42000,   # <= 45000
    )


def test_valid_load_passes_validation(valid_freight_data):
    """A valid load with matching finances, legal weight, and complete data must pass."""
    result = validate_freight_data(valid_freight_data)
    assert result.is_valid is True
    assert len(result.issues) == 0


def test_rate_mismatch_triggers_error(valid_freight_data):
    """When linehaul + fuel does not equal total pay, RATE_MISMATCH must be generated."""
    valid_freight_data.total_linehaul_rate = 2200.0
    valid_freight_data.fuel_surcharge = 350.0
    valid_freight_data.total_pay = 2800.0  # Mismatch: 2200 + 350 != 2800

    result = validate_freight_data(valid_freight_data)
    assert result.is_valid is False
    assert len(result.issues) == 1

    issue = result.issues[0]
    assert issue.code == "RATE_MISMATCH"
    assert issue.severity == IssueSeverity.ERROR
    assert "2,200.00" in issue.message
    assert "350.00" in issue.message
    assert "2,800.00" in issue.message


def test_overweight_load_triggers_warning(valid_freight_data):
    """When weight exceeds 45,000 lbs, OVERWEIGHT_LOAD warning must be generated."""
    valid_freight_data.weight_lbs = 46800

    result = validate_freight_data(valid_freight_data)
    assert result.is_valid is False  # Warnings also make is_valid False
    assert len(result.issues) == 1

    issue = result.issues[0]
    assert issue.code == "OVERWEIGHT_LOAD"
    assert issue.severity == IssueSeverity.WARNING
    assert "46,800" in issue.message
    assert "45,000" in issue.message


def test_incomplete_data_missing_fields(valid_freight_data):
    """Missing or empty string fields must trigger INCOMPLETE_DATA."""
    valid_freight_data.carrier_name = ""
    valid_freight_data.load_number = "   "
    valid_freight_data.pickup_location.zip = ""

    result = validate_freight_data(valid_freight_data)
    assert result.is_valid is False

    issue_codes = [issue.code for issue in result.issues]
    assert "INCOMPLETE_DATA" in issue_codes

    incomplete_issue = next(i for i in result.issues if i.code == "INCOMPLETE_DATA")
    assert incomplete_issue.severity == IssueSeverity.ERROR
    assert "carrier_name" in incomplete_issue.message
    assert "load_number" in incomplete_issue.message
    assert "pickup_location.zip" in incomplete_issue.message


def test_combined_sample_document_validation():
    """Test using the exact sample document values: 2200 + 350 vs 2800 and 46,800 lbs."""
    sample_data = ExtractedFreightData(
        carrier_name="Apex Logistics Solutions LLC",
        load_number="LD-994821",
        pickup_location=Location(city="Dallas", state="TX", zip="75201"),
        delivery_location=Location(city="Atlanta", state="GA", zip="30303"),
        total_linehaul_rate=2200.0,
        fuel_surcharge=350.0,
        total_pay=2800.0,
        weight_lbs=46800,
    )

    result = validate_freight_data(sample_data)
    assert result.is_valid is False
    assert len(result.issues) == 2

    codes = {issue.code for issue in result.issues}
    assert codes == {"RATE_MISMATCH", "OVERWEIGHT_LOAD"}


def test_monetary_floating_point_tolerance(valid_freight_data):
    """Ensure floating-point arithmetic imprecision (e.g. 1000.10 + 200.20 == 1200.30) does not produce false positives."""
    valid_freight_data.total_linehaul_rate = 1000.10
    valid_freight_data.fuel_surcharge = 200.20
    valid_freight_data.total_pay = 1200.30

    result = validate_freight_data(valid_freight_data)
    assert result.is_valid is True
    assert len(result.issues) == 0
