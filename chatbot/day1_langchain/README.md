# Day 1 – LangChain building blocks: Loan Enquiry Reader

## What I built

A reader that turns messy loan-enquiry emails into a typed `LoanEnquiry` object
(name, amount in rupees, tenure in months, purpose, confidence, missing fields)
using a prompt template piped into `with_structured_output`. It never guesses
missing values, processes all emails with `.batch`, and falls back to a clean
"could not read" result after one retry.

## How to run

From the `chatbot/` folder (so `.env` is found), with Ollama running:

```powershell
uv run python day1_langchain/enquiry_reader.py
```

The results table is printed and saved to `day1_langchain/results.txt`.
The script ends with `All asserts passed.` when every check succeeds.

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

Input data: `../data/enquiries.txt` (five sample emails, one per line).

## Model and tracing

- Model: `ollama:qwen3.5:9b` (local), with `reasoning=False` so the answer lands in `.content`
- Tracing: LangSmith project `langchain-week`

## One thing that surprised me

<!-- Write this in your own words. -->
