# LangChain & LangGraph week – Loan Assistant

Five days, one project: each day builds one piece of a loan assistant, and
Friday joins them together.

| Day | Folder | Builds |
|---|---|---|
| Mon | `day1_langchain/` | Loan-enquiry reader (typed output from messy text) |
| Tue | `day2_agents/` | Agent with tools (EMI, eligibility, customer lookup) |
| Wed | `day3_rag/` | Policy Q&A with citations (RAG) |
| Thu | `day4_langgraph/` | Pre-screening workflow (LangGraph) |
| Fri | `day5_capstone/` | Human approval, memory, tracing, capstone |

## Setup

1. Install and start [Ollama](https://ollama.com), then pull the model:
   `ollama pull qwen3.5:9b`
2. Install dependencies from the repo root: `uv sync`
3. Create `chatbot/.env` (git-ignored) with:

   ```
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=<your key>
   LANGSMITH_PROJECT=langchain-week
   ```

4. Smoke test, from this folder: `uv run python hello.py`

Run every script from this `chatbot/` folder so `.env` is picked up.
Each day's folder has its own README with run instructions.

## Data

`data/` holds the sample data from the guide only. No real customer data.
