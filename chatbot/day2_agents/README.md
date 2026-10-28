# Day 2 – Tools and agents: Loan Helper Agent

## What I built

A loan helper agent with three tools: `get_customer`, `emi_calculator` and
`check_eligibility`. The model reads the question and decides which tools to
call and in what order; the tools do every calculation and apply the rules, so
no number in an answer comes from the model itself. The agent only talks about
loans, asks for missing details instead of guessing, and says plainly when a
customer is not found.

Eligibility rules (the tool checks all of them and lists every failure): age
21 to 60, income at least 25,000 a month, credit score at least 700, and
existing EMI plus new EMI at most 50% of monthly income.

## How to run

From the `chatbot/` folder (so `.env` is found), with Ollama running:

```powershell
uv run python day2_agents/tools.py        # test the tools alone, no AI (instant)
uv run python day2_agents/loan_agent.py   # the agent on the guide's 6 questions
uv run python day2_agents/loan_agent.py --chat   # ask your own questions; type exit to quit
```

In chat mode the agent remembers the conversation, so it can ask for missing
details and use your reply. Every tool call and tool result is printed before
the answer.

`loan_agent.py` prints each question's tool calls, saves them to
`day2_agents/traces.txt` and ends with `All asserts passed.` when all six rows
behave as expected.

## Files

| File | What it shows |
|---|---|
| `lab1_tools.py` | `@tool`: the model only sees the tool's name, description and args |
| `lab2_agent.py` | A first agent with `create_agent`; its answer matches Lab 1 |
| `lab3_messages.py` | Every message in the loop, labelled: human request, tool call, tool result, final answer |
| `lab4_docstring.py` | The same question with the real docstring and with `"does maths"` |
| `lab5_errors.py` | A tool that raises crashes the agent; one that returns a message lets the agent ask the user to fix it |
| `tools.py` | The three assignment tools, plus a self-test without the AI |
| `loan_agent.py` | The assignment: agent, system prompt, the guide's 6 questions, retry and fallback, asserts |
| `traces.txt` | Saved output of `loan_agent.py`: every tool call and result per question |
| `NOTE.md` | Five lines: what would break if the tool descriptions were vague |
| `trace_lab5_errors.png` | LangSmith trace of Lab 5: the tool returns "Tenure must be positive" and the agent asks the user to fix it |

The tool-call order for questions 2 and 3 (`get_customer` → `emi_calculator` →
`check_eligibility`) is in `traces.txt`, and in LangSmith under the `LangGraph`
runs for those two questions.

Customer data: `../data/customers.py` (the guide's mock customers C101 to C104).

## Results

| # | Question | Tools called, in order | Behaviour |
|---|---|---|---|
| 1 | EMI for 3,00,000 at 10.5% for 24 months? | `emi_calculator` | ₹13,912.81 |
| 2 | Is C101 eligible for 5,00,000 at 11% for 36 months? | `get_customer`, `emi_calculator`, `check_eligibility` | Eligible (burden 33.4%) |
| 3 | Is C103 eligible for 4,00,000 at 11% for 24 months? | `get_customer`, `emi_calculator`, `check_eligibility` | Not eligible: credit score 680 and burden 101.6% |
| 4 | Is C999 eligible for a loan? | `get_customer` | Customer not found, nothing invented |
| 5 | What is the capital of France? | none | Politely declines |
| 6 | Can I get a loan? | none | Asks for the customer ID |

## Model and tracing

- Model: `ollama:qwen3.5:9b` (local), `reasoning=False`, `temperature=0`
- Tracing: LangSmith project `langchain-week`

## One thing that surprised me

In Lab 4 I replaced the EMI tool's docstring with just "does maths" and expected
the agent to break, but it still called the tool with 11 and 36 and got the
right EMI: the argument names (`annual_rate_percent`, `tenure_months`) were
enough of a hint on their own. The other surprise was question 5: told to stay
on loan topics, the agent politely declined and then answered "Paris" anyway,
until the prompt said not to answer off-topic questions at all.
