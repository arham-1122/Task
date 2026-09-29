"""Tests for Pydantic data models and type validation."""

import pytest
from pydantic import ValidationError

from freight_processor.models import (
    ExtractedFreightData,
    IssueSeverity,
    Location,
    ProcessingResult,
    ProcessingStatus,
    ValidationIssue,
    ValidationResult,
)


def test_location_preserves_zip_as_string():
    """ZIP codes must remain strings to preserve leading zeros and formatting."""
    loc = Location(city="Boston", state="MA", zip="02108")
    assert loc.city == "Boston"
    assert loc.state == "MA"
    assert loc.zip == "02108"
    assert isinstance(loc.zip, str)


def test_extracted_freight_data_allows_mismatched_math():
    """ExtractedFreightData must represent literal values without validating arithmetic."""
    data = ExtractedFreightData(
        carrier_name="Apex Logistics Solutions LLC",
        load_number="LD-994821",
        pickup_location=Location(city="Dallas", state="TX", zip="75201"),
        delivery_location=Location(city="Atlanta", state="GA", zip="30303"),
        total_linehaul_rate=2200.0,
        fuel_surcharge=350.0,
        total_pay=2800.0,  # 2200 + 350 != 2800, model should still instantiate cleanly
        weight_lbs=46800,
    )
    assert data.total_linehaul_rate == 2200.0
    assert data.fuel_surcharge == 350.0
    assert data.total_pay == 2800.0
    assert data.weight_lbs == 46800


def test_extracted_freight_data_type_coercion():
    """String numeric values should coerce appropriately in Pydantic."""
    data = ExtractedFreightData(
        carrier_name="Carrier Co",
        load_number="12345",
        pickup_location={"city": "Dallas", "state": "TX", "zip": "75201"},
        delivery_location={"city": "Atlanta", "state": "GA", "zip": "30303"},
        total_linehaul_rate="1500.50",
        fuel_surcharge="250.00",
        total_pay="1750.50",
        weight_lbs="35000",
    )
    assert isinstance(data.total_linehaul_rate, float)
    assert isinstance(data.weight_lbs, int)
    assert isinstance(data.pickup_location, Location)


def test_extracted_freight_data_missing_fields_raises_validation_error():
    """Omitting required fields should raise a ValidationError."""
    with pytest.raises(ValidationError):
        ExtractedFreightData(
            carrier_name="Carrier Co",
            # missing load_number and other required fields
        )


def test_validation_issue_and_result():
    """ValidationIssue and ValidationResult should structure diagnostic findings."""
    issue = ValidationIssue(
        code="RATE_MISMATCH",
        severity=IssueSeverity.ERROR,
        message="Total pay 2800.0 != linehaul 2200.0 + fuel 350.0",
    )
    result = ValidationResult(is_valid=False, issues=[issue])
    assert not result.is_valid
    assert len(result.issues) == 1
    assert result.issues[0].code == "RATE_MISMATCH"


def test_processing_result():
    """ProcessingResult should capture the final disposition and issues."""
    data = ExtractedFreightData(
        carrier_name="Carrier Co",
        load_number="LD-001",
        pickup_location=Location(city="Chicago", state="IL", zip="60601"),
        delivery_location=Location(city="Detroit", state="MI", zip="48201"),
        total_linehaul_rate=1000.0,
        fuel_surcharge=100.0,
        total_pay=1100.0,
        weight_lbs=30000,
    )
    res = ProcessingResult(
        status=ProcessingStatus.APPROVED,
        extracted_data=data,
        issues=[],
    )
    assert res.status == ProcessingStatus.APPROVED
    assert res.extracted_data.carrier_name == "Carrier Co"
    assert len(res.issues) == 0
