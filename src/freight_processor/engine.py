"""Pipeline orchestration engine connecting extraction, validation, and decision logic."""

from typing import Any, Optional

from freight_processor.extractor import ExtractionError, extract_freight_data
from freight_processor.models import (
    IssueSeverity,
    ProcessingResult,
    ProcessingStatus,
    ValidationIssue,
)
from freight_processor.validator import validate_freight_data


def process_freight_document(
    raw_text: str,
    client: Optional[Any] = None,
) -> ProcessingResult:
    """Process a raw freight document through extraction, validation, and final disposition.

    Pipeline steps:
    1. Extract structured data from raw text using the LLM extraction layer.
    2. Handle any extraction or format errors by routing directly to human review with diagnostic issues.
    3. Run deterministic business-rule validation against extracted fields.
    4. Formulate the final automated disposition:
       - APPROVED: 0 validation issues
       - FLAGGED_FOR_HUMAN_REVIEW: >= 1 validation issue (errors or warnings)

    Args:
        raw_text: Raw text content from the freight document.
        client: Optional pre-configured client or mock for the extraction layer.

    Returns:
        ProcessingResult: The final structured outcome containing status, extracted data, and issues.
    """
    # Step 1: Extraction Layer
    try:
        extracted_data = extract_freight_data(raw_text=raw_text, client=client)
    except (ExtractionError, ValueError) as exc:
        return ProcessingResult(
            status=ProcessingStatus.FLAGGED_FOR_HUMAN_REVIEW,
            extracted_data=None,
            issues=[
                ValidationIssue(
                    code="EXTRACTION_ERROR",
                    severity=IssueSeverity.ERROR,
                    message=f"Document extraction failed: {exc}",
                )
            ],
        )

    # Step 2: Deterministic Business-Rule Validation
    validation_result = validate_freight_data(extracted_data)

    # Step 3: Decision Engine
    status = (
        ProcessingStatus.APPROVED
        if validation_result.is_valid
        else ProcessingStatus.FLAGGED_FOR_HUMAN_REVIEW
    )

    return ProcessingResult(
        status=status,
        extracted_data=extracted_data,
        issues=validation_result.issues,
    )
