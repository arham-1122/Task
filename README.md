# Freight Document Extraction & Validation System

A lightweight, robust Python system designed to extract structured data from unstructured/messy operational freight documents using Google Gemini, enforce strict Pydantic v2 schemas, apply deterministic business-rule validations, and produce an automated review decision.

---

## Project Purpose

Automate the ingestion and verification of freight load confirmations and rate sheets by:
1. Extracting core operational and financial data points accurately without hallucination or premature math corrections.
2. Validating extracted data against strict typing schemas.
3. Running deterministic business logic (rate arithmetic, weight thresholds, completeness).
4. Emitting an automated disposition (`APPROVED` vs `FLAGGED_FOR_HUMAN_REVIEW`) along with explicit diagnostic flags.

---

## Planned Pipeline Architecture

```
[Raw Document Text]
        │
        ▼
[LLM Extractor (Google Gemini)]
  • Literal structured extraction via JSON schema / Structured Outputs (Pydantic)
        │
        ▼
[Schema Validation (Pydantic v2)]
  • Type enforcement and structured sub-models (Location: city, state, zip)
        │
        ▼
[Deterministic Business Rule Validator]
  • Math Check: total_linehaul_rate + fuel_surcharge == total_pay  --> RATE_MISMATCH
  • Weight Check: weight_lbs > 45,000                             --> OVERWEIGHT_LOAD
  • Missing/Ambiguity Check: missing required fields or locations  --> INCOMPLETE_DATA
        │
        ▼
[Decision Engine]
  • No flags   --> APPROVED
  • ≥ 1 flag   --> FLAGGED_FOR_HUMAN_REVIEW
        │
        ▼
[CLI / Structured JSON Output]
```

---

## Environment & API Setup

This project uses the official **Google Gemini API**, which provides a free tier suitable for running tests and demonstrations without requiring paid API credits.

1. **Obtain an API Key:**
   * Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/).

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   # Set GEMINI_API_KEY with your key in .env
   ```

---

## Note on Implementation

> **Status:** Project foundation created. Implementation of LLM extraction, Pydantic schemas, validation rules, CLI runner, and test suite will be completed incrementally in subsequent stages.
