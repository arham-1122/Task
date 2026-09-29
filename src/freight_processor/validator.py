"""Deterministic business-rule validation logic for freight document processing."""

import math
from typing import List

from freight_processor.models import (
    ExtractedFreightData,
    IssueSeverity,
    ValidationIssue,
    ValidationResult,
)

# Constants for business rules
MAX_WEIGHT_LBS = 45000
CURRENCY_TOLERANCE = 0.01  # 1 cent tolerance for float arithmetic


def validate_freight_data(data: ExtractedFreightData) -> ValidationResult:
    """Run deterministic business-rule validations against extracted freight data.

    Rules applied:
    1. Incomplete Data Check (ERROR): Verifies required fields/locations are present and non-empty.
    2. Rate Mismatch Check (ERROR): Verifies total_linehaul_rate + fuel_surcharge == total_pay.
    3. Overweight Load Check (WARNING): Flags shipments exceeding 45,000 lbs.

    Args:
        data: Extracted freight data model.

    Returns:
        ValidationResult containing pass/fail status and all generated validation issues.
    """
    issues: List[ValidationIssue] = []

    # Rule 1: Incomplete Data Check
    missing_fields: List[str] = []

    if not data.carrier_name or not data.carrier_name.strip():
        missing_fields.append("carrier_name")
    if not data.load_number or not data.load_number.strip():
        missing_fields.append("load_number")

    # Pickup location completeness
    if not data.pickup_location.city or not data.pickup_location.city.strip():
        missing_fields.append("pickup_location.city")
    if not data.pickup_location.state or not data.pickup_location.state.strip():
        missing_fields.append("pickup_location.state")
    if not data.pickup_location.zip or not data.pickup_location.zip.strip():
        missing_fields.append("pickup_location.zip")

    # Delivery location completeness
    if not data.delivery_location.city or not data.delivery_location.city.strip():
        missing_fields.append("delivery_location.city")
    if not data.delivery_location.state or not data.delivery_location.state.strip():
        missing_fields.append("delivery_location.state")
    if not data.delivery_location.zip or not data.delivery_location.zip.strip():
        missing_fields.append("delivery_location.zip")

    if missing_fields:
        issues.append(
            ValidationIssue(
                code="INCOMPLETE_DATA",
                severity=IssueSeverity.ERROR,
                message=f"Missing or empty required field(s): {', '.join(missing_fields)}.",
            )
        )

    # Rule 2: Rate Mismatch Check (total_linehaul_rate + fuel_surcharge == total_pay)
    calculated_total = data.total_linehaul_rate + data.fuel_surcharge
    rate_diff = abs(calculated_total - data.total_pay)

    if rate_diff >= CURRENCY_TOLERANCE:
        issues.append(
            ValidationIssue(
                code="RATE_MISMATCH",
                severity=IssueSeverity.ERROR,
                message=(
                    f"Rate calculation mismatch: Stated total pay (${data.total_pay:,.2f}) does not equal "
                    f"linehaul (${data.total_linehaul_rate:,.2f}) + fuel surcharge (${data.fuel_surcharge:,.2f}) "
                    f"= ${calculated_total:,.2f} (difference of ${rate_diff:,.2f})."
                ),
            )
        )

    # Rule 3: Overweight Load Check (weight_lbs > 45,000)
    if data.weight_lbs > MAX_WEIGHT_LBS:
        issues.append(
            ValidationIssue(
                code="OVERWEIGHT_LOAD",
                severity=IssueSeverity.WARNING,
                message=(
                    f"Overweight load: Stated weight of {data.weight_lbs:,} lbs exceeds "
                    f"the maximum allowable threshold of {MAX_WEIGHT_LBS:,} lbs."
                ),
            )
        )

    # is_valid is True only when there are ZERO errors and ZERO warnings
    is_valid = len(issues) == 0

    return ValidationResult(
        is_valid=is_valid,
        issues=issues,
    )
