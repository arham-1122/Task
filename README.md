# Freight Document Extraction & Validation System

A lightweight Python application that extracts structured data from unstructured freight documents using Google Gemini, enforces a strict Pydantic v2 schema, validates the extracted data against deterministic business rules, and produces an automated processing decision.

The system is designed around a simple principle: **use the LLM for semantic extraction and deterministic Python code for business decisions**. This prevents the language model from silently correcting financial values or making business-rule decisions.

---

## Overview

The application processes freight documents through the following pipeline:

```text
Raw Freight Document
        │
        ▼
LLM Extraction — Google Gemini
        │
        ▼
Structured Pydantic Model
        │
        ▼
Deterministic Validation
        │
        ▼
Decision Engine
        │
        ▼
APPROVED / FLAGGED_FOR_HUMAN_REVIEW
        │
        ▼
CLI / JSON Output
```

The system extracts:

* `carrier_name`
* `load_number`
* `pickup_location`
* `delivery_location`
* `total_linehaul_rate`
* `fuel_surcharge`
* `total_pay`
* `weight_lbs`

---

## Project Structure

```text
Task/
├── data/
│   └── sample_freight_doc.txt
│
├── src/
│   └── freight_processor/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       ├── extractor.py
│       ├── validator.py
│       ├── engine.py
│       └── cli.py
│
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_validator.py
│   ├── test_extractor.py
│   ├── test_engine.py
│   └── test_end_to_end.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

### Component Responsibilities

* **`models.py`** — Defines strict Pydantic models and application result types.
* **`extractor.py`** — Handles Google Gemini structured extraction and converts model output into the Pydantic schema.
* **`validator.py`** — Contains deterministic freight business rules.
* **`engine.py`** — Orchestrates extraction, validation, and final decision-making.
* **`cli.py`** — Provides the command-line interface.
* **`tests/`** — Contains unit, integration, and deterministic end-to-end tests.

---

## Technology Stack

* **Python 3.10+**
* **Google Gemini**
* **`google-genai`**
* **Pydantic v2**
* **python-dotenv**
* **pytest**
* **argparse**
* **JSON**

---

## Environment Setup

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd Task
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### Windows PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Gemini

Create a `.env` file from the provided example:

```bash
cp .env.example .env
```

On Windows, you can also create `.env` manually from `.env.example`.

Set:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=your_supported_gemini_model
```

Do **not** commit `.env` or expose your API key.

---

## Running the Application

The CLI accepts a raw freight document as a text file.

### Human-readable output

```bash
python -m freight_processor.cli data/sample_freight_doc.txt
```

### JSON output

```bash
python -m freight_processor.cli data/sample_freight_doc.txt --json
```

---

## Validation Rules

The validation layer is deterministic and does not rely on the LLM for business decisions.

### 1. Rate mismatch

The application checks:

```text
total_linehaul_rate + fuel_surcharge == total_pay
```

If the values do not match:

```text
RATE_MISMATCH
```

is generated as an error.

### 2. Overweight load

If:

```text
weight_lbs > 45,000
```

the system generates:

```text
OVERWEIGHT_LOAD
```

as a warning.

### 3. Incomplete data

Missing or blank required information, including load numbers or locations, produces:

```text
INCOMPLETE_DATA
```

as an error.

### 4. Final decision

If no errors or warnings exist:

```text
APPROVED
```

If any validation issue exists:

```text
FLAGGED_FOR_HUMAN_REVIEW
```

The resulting issues include a code, severity, and explanatory message.

---

## Sample Document

The included sample document intentionally contains validation problems.

Relevant values:

```text
Linehaul Rate:       $2,200.00
Fuel Surcharge:        $350.00
Total Agreed Amount: $2,800.00
Total Weight:         46,800 lbs
```

The arithmetic is:

```text
$2,200 + $350 = $2,550
```

but the document states:

```text
Total Pay = $2,800
```

Therefore, the system must preserve the document's stated `$2,800` value and allow the deterministic validator to identify the discrepancy.

The weight also exceeds the 45,000 lb threshold.

### Expected decision

```text
FLAGGED_FOR_HUMAN_REVIEW
```

with:

```text
RATE_MISMATCH
OVERWEIGHT_LOAD
```

---

## Example Output

A successful run against the provided sample produces a result equivalent to:

```json
{
  "status": "FLAGGED_FOR_HUMAN_REVIEW",
  "extracted_data": {
    "carrier_name": "Apex Logistics Solutions LLC",
    "load_number": "LD-994821",
    "pickup_location": {
      "city": "Dallas",
      "state": "TX",
      "zip": "75201"
    },
    "delivery_location": {
      "city": "Atlanta",
      "state": "GA",
      "zip": "30303"
    },
    "total_linehaul_rate": 2200.0,
    "fuel_surcharge": 350.0,
    "total_pay": 2800.0,
    "weight_lbs": 46800
  },
  "issues": [
    {
      "code": "RATE_MISMATCH",
      "severity": "ERROR"
    },
    {
      "code": "OVERWEIGHT_LOAD",
      "severity": "WARNING"
    }
  ]
}
```

The important behavior is that `total_pay` remains `2800.0`; the application does not allow the LLM to silently recalculate or correct the value.

---

## Testing

Run the complete automated test suite with:

```bash
pytest -q
```

The current test suite contains **22 tests**, covering the data models, validation rules, extraction layer, processing engine, CLI-related behavior, and deterministic end-to-end processing.

The latest verification completed with:

```text
22 passed
```

The end-to-end test uses a mocked extraction layer, so it does not require a live Gemini API call.

---

## Architecture & LLM Reliability

The application separates probabilistic LLM behavior from deterministic application logic. Google Gemini is responsible for interpreting unstructured freight text and extracting the required fields. The extraction request uses a structured JSON response configuration based on the Pydantic model, while the resulting data is validated again before it enters the business-rule layer. The extraction prompt explicitly instructs the model to preserve values exactly as stated in the source document and not recalculate or reconcile financial values.

Business rules are intentionally implemented outside the LLM in deterministic Python code. This makes financial calculations, weight thresholds, completeness checks, and final approval decisions predictable and testable. The orchestration layer also converts extraction failures into a reviewable processing result instead of allowing an external LLM failure to silently produce an incorrect approval.

---

## Scaling to 100,000 Documents per Day

For a production workload of approximately 100,000 messy PDF documents per day, the synchronous CLI architecture could be evolved into an asynchronous, horizontally scalable pipeline. Uploaded documents could first be stored in object storage, with document-processing jobs placed onto a durable message queue. A pool of workers could then perform PDF text extraction/OCR, followed by LLM extraction and deterministic validation. Results and processing metadata could be persisted in a database while failed jobs could be retried or routed to a dead-letter queue.

At higher scale, the LLM worker layer would need rate limiting, concurrency controls, retry policies with exponential backoff, idempotency protection, and monitoring for latency, extraction failures, validation failures, and model usage. Provider-specific code is isolated in the extraction layer, allowing the system to evolve toward multiple model providers or specialized models without rewriting the validation and decision layers.

---

## Security

* API credentials are loaded through environment variables.
* `.env` is excluded from version control.
* `.env.example` contains only placeholder configuration.
* API keys should never be committed to the repository.

---

## Current Status

The core take-home requirements are implemented:

* LLM-based freight document extraction
* Strict Pydantic schema enforcement
* Deterministic validation engine
* Automated decision workflow
* CLI and JSON output
* Error handling
* Automated test suite
* Deterministic end-to-end test

**Test status: 22/22 tests passing.**
