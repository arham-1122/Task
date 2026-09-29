"""LLM-based structured data extraction layer using Google Gemini."""

import time
from typing import Any, Optional
from pydantic import ValidationError

from freight_processor.config import GEMINI_API_KEY, GEMINI_MODEL
from freight_processor.models import ExtractedFreightData

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class ExtractionError(Exception):
    """Raised when structured extraction from raw document text fails."""
    pass


EXTRACTION_SYSTEM_INSTRUCTION = """You are a specialized freight document extraction engine.
Your sole task is to extract structured data strictly and literally from the provided operational freight document text.

CRITICAL EXTRACTION INSTRUCTIONS:
1. Extract numerical values and text exactly as written in the source document.
2. Do NOT calculate, correct, reconcile, balance, or 'fix' any financial figures.
3. Do NOT infer a mathematically corrected total amount. If the document states Linehaul = 2200, Fuel Surcharge = 350, and Total Pay / Agreed Amount = 2800, you MUST extract total_linehaul_rate=2200.0, fuel_surcharge=350.0, and total_pay=2800.0.
4. Downstream deterministic validation systems are responsible for arithmetic verification. Your role is purely literal extraction.
5. Do NOT hallucinate or invent missing data.
6. Extract geographic locations (city, state, zip) as distinct fields. Strip street names or distribution center titles into city/state/zip components as appropriate.
7. Return only the fields defined in the structured schema.
"""


def get_gemini_client(api_key: Optional[str] = None) -> Any:
    """Initialize and return a Gemini API client."""
    if genai is None:
        raise ExtractionError(
            "The 'google-genai' library is not installed. Please run: pip install -r requirements.txt"
        )

    key = api_key if api_key is not None else GEMINI_API_KEY
    if not key:
        raise ExtractionError(
            "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your .env file or environment."
        )
    return genai.Client(api_key=key)


def extract_freight_data(
    raw_text: str,
    client: Optional[Any] = None,
    model_name: Optional[str] = None,
    max_retries: int = 3,
) -> ExtractedFreightData:
    """Extract structured freight data from raw document text using Gemini.

    Args:
        raw_text: The unstructured/semi-structured text of a freight document.
        client: Optional pre-configured Gemini client or mock instance.
        model_name: Optional override for the Gemini model identifier.
        max_retries: Number of retry attempts on transient 503/429 errors.

    Returns:
        ExtractedFreightData: Populated and schema-validated Pydantic model instance.

    Raises:
        ValueError: If raw_text is empty or contains only whitespace.
        ExtractionError: If the API call fails or the output cannot be validated into ExtractedFreightData.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text cannot be empty or contain only whitespace.")

    active_client = client or get_gemini_client()
    target_model = model_name or GEMINI_MODEL

    user_prompt = f"Please extract structured freight data from the following document text:\n\n{raw_text.strip()}"

    response = None
    last_exception = None

    for attempt in range(max_retries):
        try:
            if types is not None:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedFreightData,
                    temperature=0.0,
                    system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
                )
                response = active_client.models.generate_content(
                    model=target_model,
                    contents=user_prompt,
                    config=config,
                )
            else:
                response = active_client.models.generate_content(
                    model=target_model,
                    contents=user_prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": ExtractedFreightData,
                        "temperature": 0.0,
                        "system_instruction": EXTRACTION_SYSTEM_INSTRUCTION,
                    },
                )
            break  # Success
        except Exception as exc:
            last_exception = exc
            exc_str = str(exc)
            # Retry only on transient capacity/rate-limit errors
            if ("503" in exc_str or "429" in exc_str or "UNAVAILABLE" in exc_str) and attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise ExtractionError(f"Gemini API request failed: {exc}") from exc

    if response is None:
        raise ExtractionError(f"Gemini API request failed after {max_retries} attempts: {last_exception}")

    if not response or not getattr(response, "text", None):
        raise ExtractionError("Gemini returned an empty response.")

    try:
        # If SDK parsed object directly into model
        if hasattr(response, "parsed") and isinstance(response.parsed, ExtractedFreightData):
            return response.parsed

        # Fallback to validating JSON string
        return ExtractedFreightData.model_validate_json(response.text)
    except (ValidationError, Exception) as exc:
        raise ExtractionError(f"Failed to validate LLM output into ExtractedFreightData: {exc}") from exc
