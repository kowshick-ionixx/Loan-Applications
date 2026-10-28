# Day 1 – LangChain building blocks: Loan Enquiry Reader

## What I built

A reader that turns messy loan-enquiry emails into a typed `LoanEnquiry` object
(name, amount in rupees, tenure in months, purpose, confidence, missing fields)
using a prompt template piped into `with_structured_output`. It never guesses
missing values, processes all five emails with `.batch`, retries once on
failure and then falls back to a clean "could not read" result.

## How to run

From the `chatbot/` folder (so `.env` is found), with Ollama running:

```powershell
uv run python day1_langchain/enquiry_reader.py
```

The results table is printed and saved to `day1_langchain/results.txt`.
The script ends with `All asserts passed.` when every check succeeds.

## What I completed

| Guide item | Done in | Result |
|---|---|---|
| Lab 1: Messages | `lab1_messages.py` | Same question, formal vs casual reply from two system messages |
| Lab 2: Prompt template | `lab2_prompt_template.py` | One `{email}` template, three outputs |
| Lab 3: Structured output | `lab3_structured_output.py` | `type(result)` is `LoanEnquiry`, not `str` |
| Lab 4: Chain it | `lab4_chain.py` | `prompt \| extractor`, `.batch` returns 3 objects, `model.stream` prints gradually |
| Lab 5: Read a trace | `trace_screenshot.png` | LangSmith trace showing the system message and token count |
| Assignment: Loan Enquiry Reader | `enquiry_reader.py` | All six requirements below |

Assignment requirements:

1. `LoanEnquiry` with the four fields plus `confidence` (high, medium, low) and `missing_fields`
2. A prompt template that tells the model never to guess missing values
3. `read_enquiry(text) -> LoanEnquiry`
4. All five emails processed with `.batch` and printed as a table
5. One retry, then a clean "could not read" result, proved with an empty string
6. Asserts: emails 1 and 2 have every field filled, email 4's `missing_fields` contains `amount`,
   25L converts to 2,500,000 and 5 years to 60 months

## Results

| # | Name | Amount | Months | Purpose | Confidence | Missing |
|---|---|---|---|---|---|---|
| 1 | Ramesh Kumar | 5,00,000 | 36 | house renovation | high | - |
| 2 | Anita Sharma | 12,00,000 | 60 | sister's wedding | high | - |
| 3 | Imran | 2,00,000 | 18 | shop | high | - |
| 4 | Priya | - | - | buying a two-wheeler | low | amount, tenure_months |
| 5 | Suresh | 25,00,000 | 60 | Business expansion | high | - |

An empty string gives the fallback: every field empty, confidence `low`, all
four fields listed as missing.

## Files

| File | What it shows |
|---|---|
| `lab1_messages.py` | Same question, two system messages: formal vs casual reply |
| `lab2_prompt_template.py` | One `ChatPromptTemplate` with an `{email}` blank, run on three emails |
| `lab3_structured_output.py` | `with_structured_output(LoanEnquiry)` returns a typed object, not a string |
| `lab4_chain.py` | `prompt \| extractor` chain, `.batch` over three emails, `model.stream` |
| `enquiry_reader.py` | The assignment: `read_enquiry(text) -> LoanEnquiry`, batch, table, retry and fallback, asserts |
| `results.txt` | Saved output of `enquiry_reader.py` |
| `trace_screenshot.png` | A LangSmith trace showing the system message and token count |

Input data: `../data/enquiries.txt` (the guide's five sample emails, one per line).

## Model and tracing

- Model: `ollama:qwen3.5:9b` (local), `reasoning=False` so the answer lands in `.content`,
  `temperature=0` for repeatable extraction
- Structured output uses `method="function_calling"`: 5/5 emails correct, against 2/5
  with the default `json_schema` method on this model
- Tracing: LangSmith project `langchain-week`

## One thing that surprised me

The way structured output is requested mattered more than the prompt: with the
default `json_schema` method the local model got only 2 of 5 emails right, and
switching to `function_calling` made it 5 of 5 without changing a word of the
prompt. I was also surprised that a model told it works at a bank, but not
which country, answered with American documents like W-2s.
