"""Pydantic schemas and typed data models for freight document processing."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ProcessingStatus(str, Enum):
    """Terminal decision status for the processed document."""
    APPROVED = "APPROVED"
    FLAGGED_FOR_HUMAN_REVIEW = "FLAGGED_FOR_HUMAN_REVIEW"


class Location(BaseModel):
    """Geographic location breakdown for pickup and delivery stops."""

    city: str = Field(
        ...,
        description="City name (e.g., Dallas, Atlanta)",
    )
    state: str = Field(
        ...,
        description="State code or name (e.g., TX, GA)",
    )
    zip: str = Field(
        ...,
        description="Postal ZIP code as a string (e.g., '75201', '03001')",
    )


class ExtractedFreightData(BaseModel):
    """Structured data extracted literally from the freight document.

    Note: This model represents the raw stated facts in the document.
    It does not calculate, correct, or sanitize values.
    """

    carrier_name: str = Field(
        ...,
        description="Legal name of the carrier company",
    )
    load_number: str = Field(
        ...,
        description="Reference or load tracking number (e.g., LD-994821)",
    )
    pickup_location: Location = Field(
        ...,
        description="Pickup origin location details",
    )
    delivery_location: Location = Field(
        ...,
        description="Delivery destination location details",
    )
    total_linehaul_rate: float = Field(
        ...,
        description="Base linehaul freight rate in USD exactly as stated on the document",
    )
    fuel_surcharge: float = Field(
        ...,
        description="Fuel surcharge amount in USD exactly as stated on the document",
    )
    total_pay: float = Field(
        ...,
        description="Total agreed compensation amount in USD exactly as stated on the document without recalculation",
    )
    weight_lbs: int = Field(
        ...,
        description="Total shipment weight in pounds (lbs) as an integer",
    )


class ValidationIssue(BaseModel):
    """A single deterministic validation finding or business rule anomaly."""

    code: str = Field(
        ...,
        description="Machine-readable issue code (e.g., RATE_MISMATCH, OVERWEIGHT_LOAD, INCOMPLETE_DATA)",
    )
    severity: IssueSeverity = Field(
        default=IssueSeverity.ERROR,
        description="Severity level of the validation issue",
    )
    message: str = Field(
        ...,
        description="Human-readable explanation of why the rule was triggered",
    )


class ValidationResult(BaseModel):
    """Aggregated output of the deterministic business-rule validation phase."""

    is_valid: bool = Field(
        ...,
        description="True if the document passed all business rules with zero errors/warnings",
    )
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="List of validation issues encountered during deterministic checks",
    )


class ProcessingResult(BaseModel):
    """Final application output encompassing extraction, validation, and disposition."""

    status: ProcessingStatus = Field(
        ...,
        description="Final automated decision disposition",
    )
    extracted_data: Optional[ExtractedFreightData] = Field(
        default=None,
        description="Structured data extracted from the document, if extraction succeeded",
    )
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="List of validation findings triggering human review or audit notes",
    )
