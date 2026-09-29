# Freight Document Extraction & Validation System

A small Python application that reads freight document text, extracts the required information using Google Gemini, checks the extracted data against business rules, and returns a final decision.

The main goal is to keep the LLM responsible for **extracting information**, while Python handles the **actual validation and decision-making**.

## How It Works

```text
Freight Document
       ↓
   Read Text
       ↓
 Gemini Extraction
       ↓
 Pydantic Validation
       ↓
 Business Rule Checks
       ↓
 Approved / Flagged for Human Review
```

The system extracts:

* Carrier name
* Load number
* Pickup location
* Delivery location
* Linehaul rate
* Fuel surcharge
* Total pay
* Weight

It then checks the extracted data for missing information, incorrect rate calculations, and overweight loads.

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

### Main files

* `models.py` — Pydantic models used for the extracted data and processing results.
* `extractor.py` — Sends the document text to Gemini and converts the response into the required schema.
* `validator.py` — Contains the freight business rules.
* `engine.py` — Connects extraction, validation, and the final decision.
* `cli.py` — Command-line interface for running the processor.
* `tests/` — Unit and end-to-end tests.

---

## Requirements

* Python 3.10+
* Google Gemini API key

The project was developed and tested with Python 3.12.

---

## Setup

Clone the repository and move into the project directory:

```bash
git clone <repository-url>
cd Task
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.8-flash
```

Do not commit the `.env` file or your API key.

---

## Running the Application

Run the sample document:

```bash
python -m freight_processor.cli data/sample_freight_doc.txt
```

To get the result as JSON:

```bash
python -m freight_processor.cli data/sample_freight_doc.txt --json
```

---

## Validation Rules

The application currently checks three main cases.

### Rate mismatch

The linehaul rate and fuel surcharge must equal the total pay.

```text
linehaul + fuel surcharge = total pay
```

If they do not match:

```text
RATE_MISMATCH
```

### Overweight load

Loads above 45,000 lbs are flagged:

```text
OVERWEIGHT_LOAD
```

### Incomplete data

If required information such as the load number, carrier, or location is missing or incomplete:

```text
INCOMPLETE_DATA
```

If there are no issues, the result is:

```text
APPROVED
```

If there is at least one error or warning:

```text
FLAGGED_FOR_HUMAN_REVIEW
```

---

## Sample Result

The included sample document contains:

```text
Linehaul Rate:       $2,200.00
Fuel Surcharge:      $350.00
Total Agreed Amount: $2,800.00
Weight:              46,800 lbs
```

The system keeps these values exactly as they appear in the document.

It does **not** change the total pay to `$2,550`. Instead, Python detects that:

```text
2200 + 350 = 2550
```

while the document states:

```text
2800
```

The result is therefore:

```text
FLAGGED_FOR_HUMAN_REVIEW
```

with:

```text
RATE_MISMATCH
OVERWEIGHT_LOAD
```

---

## Testing

Run the full test suite with:

```bash
pytest -q
```

The current test suite covers the Pydantic models, validation rules, Gemini extraction handling, processing engine, and an end-to-end sample document test.

The tests mock the Gemini response where appropriate, so most tests do not require an API call.

---

## Architecture & LLM Reliability

The system uses Gemini to extract information from freight documents and Python to handle the actual business rules. Gemini returns the required fields in a fixed Pydantic schema, and the extracted data is validated before being processed. The prompt also tells the model to keep values exactly as they appear in the document instead of changing or recalculating them.

The business rules are handled separately in Python. This keeps checks like rate calculations, weight limits, missing data, and approval decisions consistent and easy to test. If the LLM fails, the system flags the document for human review instead of making an automatic decision.

---

## Scaling to 100,000 Documents per Day

For 100,000 documents per day, the current CLI-based setup could be changed to an asynchronous pipeline. Documents would be stored in object storage and processing jobs would be added to a message queue. Workers could then handle PDF text extraction or OCR, Gemini extraction, validation, and result storage. Failed jobs could be retried or moved to a dead-letter queue.

At this scale, the system would also need rate limiting, controlled concurrency, retries with backoff, idempotency, and monitoring. Since the Gemini integration is kept separate from the validation and decision logic, another LLM provider or model could be added later without changing the rest of the system.

---

## Tech Stack

* Python
* Google Gemini
* Pydantic
* pytest
* python-dotenv

The project intentionally keeps the implementation small. There is no database, web framework, or additional orchestration framework because they are not needed for the current requirements.

---

## Current Status

The required extraction, validation, decision workflow, CLI, and automated tests are implemented.

The sample freight document has been tested end-to-end and correctly returns `FLAGGED_FOR_HUMAN_REVIEW` because of the rate mismatch and overweight load.
