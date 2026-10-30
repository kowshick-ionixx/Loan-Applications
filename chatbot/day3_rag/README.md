# Day 3 – RAG: Policy Q&A Assistant

## What I built

A policy Q&A assistant that answers from `data/loan_policy.txt` instead of the
model's own knowledge. The policy is split into chunks, each chunk is turned
into an embedding and stored in memory; for every question the 3 closest chunks
are fetched and the model answers only from them. `ask_policy()` returns the
answer and the list of section numbers it used, and replies "I could not find
this in the policy." when the policy does not cover the question.

The same search is wrapped as a `search_policy` tool and added to my Day 2 loan
agent, so one agent can now look up policy rules and calculate EMIs.

## How to run

From the `chatbot/` folder (so `.env` is found), with Ollama running and the
embedding model pulled (`ollama pull nomic-embed-text`):

```powershell
uv run python day3_rag/policy_index.py     # build the index, check the top hit for "money paid out" is 5.1
uv run python day3_rag/policy_qa.py        # ask_policy on one found and one not-found question
uv run python day3_rag/run_questions.py    # the guide's 10 questions, saved to answers.md
uv run python day3_rag/combined_agent.py   # Day 2 agent + search_policy; type your questions, exit to quit
```

`combined_agent.py` imports the Day 2 agent, so the customer database must be
running too. The guide's demo question for it:
"I want 6,00,000 for 36 months at 11%. What is the EMI and the processing fee?"

## Files

| File | What it shows |
|---|---|
| `lab1_split.py` | Load the policy and split it into 300-character chunks with 50 characters of overlap |
| `lab2_search.py` | Embed the chunks and search by meaning: "money paid out" finds the disbursal rule 5.1 |
| `lab3_answer.py` | `ask()`: retrieve 3 chunks, answer only from them and cite the section |
| `lab4_chunks.py` | The same search at chunk sizes 80, 300 and 2000 |
| `lab5_agent.py` | `search_policy` and `emi_calculator` in one agent; it picks the right tool |
| `policy_index.py` | `build_index(chunk_size)`: load, split, embed and store |
| `policy_tools.py` | The `search_policy` tool |
| `policy_qa.py` | `ask_policy(question, store)`: structured answer + section numbers |
| `run_questions.py` | Runs the guide's 10 questions and writes `answers.md` |
| `combined_agent.py` | The Day 2 agent with `search_policy` added (4 tools), as a chat |
| `answers.md` | Saved answers and sections for the 10 questions |
| `CHUNK_EXPERIMENT.md` | Five lines: what changed between chunk size 300 and 80, and why |

## Results

| # | Question | Sections | Behaviour |
|---|---|---|---|
| 1 | What is the minimum age? | 1.1 | 21 |
| 2 | What happens if my credit score is 680? | 1.3 | Referred to a credit officer |
| 3 | Processing fee on a 6,00,000 loan? | 3.2 | 1.5 percent plus taxes (does not work out 9,000 yet) |
| 4 | Can I prepay after 8 months? | 3.3 | Yes (misses the 2 percent charge within 12 months) |
| 5 | Income proof for self-employed? | 4.3 | Last 2 years of ITR |
| 6 | Who approves a 12,00,000 loan? | 2.3 | Senior manager |
| 7 | How long until disbursal? | 5.1 | 3 working days after documents are verified |
| 8 | Can the money go to my friend's account? | 5.2 | No, only the applicant's own account |
| 9 | Policy on gold loans? | – | "I could not find this in the policy." |
| 10 | Interest rate with a 750 score? | 3.1 | Only the 10.5 to 16 percent range, no invented rate |

## Model and tracing

- Chat model: `ollama:qwen3.5:9b` (local), `reasoning=False`, `temperature=0`
- Embedding model: `ollama:nomic-embed-text` (local)
- Vector store: `InMemoryVectorStore`, rebuilt on every run
- Tracing: LangSmith project `langchain-week`

## One thing that surprised me

At chunk size 80 the model worked out the 6,00,000 processing fee as Rs 9,000,
but at 300 it only said "1.5 percent", even though rule 3.2 was retrieved both
times. Same rule, different answer: the extra rules in the bigger chunk changed
how the model answered, so a wrong answer is not always the retriever's fault.
