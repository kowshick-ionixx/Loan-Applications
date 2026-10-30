# Day 4 – LangGraph: Loan Pre-Screening Graph

## What I built

A loan pre-screening workflow built as a LangGraph `StateGraph`, without
`create_agent`. A customer ID and a loan request go in; one of `approve`,
`refer`, `reject` or `need_info` comes out, with a plain-language reason and a
log of every step the case went through. I draw the boxes and arrows, so the
path is fixed, ordered and auditable: the model never decides the route.

The graph reads the request with my Day 1 `read_enquiry`, looks the customer up
live in the database with my Day 2 `get_customer`, works out the EMI at a fixed
11 percent with my Day 2 `emi_calculator`, and applies the eligibility rules.

## How to run

From the `chatbot/` folder (so `.env` is found), with Ollama and the customer
database running:

```powershell
uv run python day4_langgraph/run_cases.py                  # the 6 test cases, saved to test_output.txt
uv run python day4_langgraph/prescreen_graph.py            # type a customer ID and a loan request; exit to quit
uv run python day4_langgraph/prescreen_graph.py --diagram  # print the Mermaid diagram
```

Each case takes a few seconds to a minute, all of it in the `intake` model call.

## Files

| File | What it shows |
|---|---|
| `lab1_smallest_graph.py` | State, two nodes, edges, `compile()` and `invoke()`: prints `{'text': 'HELLO!'}` |
| `lab2_branch.py` | `add_conditional_edges`: short and long text take different paths, shown with `stream` |
| `lab3_reducers.py` | `log` with `Annotated[list[str], operator.add]` keeps every node's entry |
| `lab4_draw.py` | `draw_mermaid()` of the Lab 2 graph, pasted into a Mermaid viewer |
| `lab5_model_node.py` | A node that calls Day 1 `read_enquiry` and stores the result in state |
| `state.py` | `LoanState`: email, customer ID, enquiry, customer, problems, EMI, failed rules, decision, reason, log |
| `nodes.py` | `intake`, `validate`, `score`, `approve`, `refer`, `reject`, `need_info` |
| `prescreen_graph.py` | The two routing functions, the wiring, `compile()`, and the interactive mode |
| `run_cases.py` | Runs the 6 cases and the rule checks, asserts every decision and saves `test_output.txt` |
| `graph.md` | The exported Mermaid diagram (picture in `graph.png`) |
| `test_output.txt` | Decision, reason and full log for each case, then the rule checks |

## Routing rules

Checked in this priority order:

| # | Condition | Decision | Checked by |
|---|---|---|---|
| 1 | Amount or tenure missing or not above 0, or customer not found | `need_info` (lists every problem) | `after_validate` |
| 2 | Fails age, income or burden, credit score below 650, amount outside 50,000 to 15,00,000 (policy 2.1) or tenure outside 12 to 60 months (policy 2.2) | `reject` (lists every failed rule) | `route` |
| 3 | Credit score 650 to 719 (policy 1.3), or amount above 10,00,000 (policy 2.3) | `refer` | `route` |
| 4 | Otherwise (credit score 720 or above) | `approve` | `route` |

Rule 1 has its own conditional edge straight after `validate`, so `score` never
runs on a missing amount or an unknown customer. `validate` stores what it found
in `problems`, so `need_info` can tell the customer exactly what to fix.

## Results

| # | Customer | Request | Expected | Path |
|---|---|---|---|---|
| 1 | 161 | 5 lakh for 3 years | approve | intake → validate → score → approve |
| 2 | 161 | 12,00,000 for 60 months | refer (amount above 10,00,000) | intake → validate → score → refer |
| 3 | 162 | 10 lakh for 36 months | reject (burden 72.8%) | intake → validate → score → reject |
| 4 | 162 | 2 lakh for 24 months | refer (credit score 701 is below 720) | intake → validate → score → refer |
| 5 | 161 | "I want a loan for a car" | need_info (amount and tenure missing) | intake → validate → need_info |
| 6 | 999 | 3 lakh for 2 years | need_info (customer not found) | intake → validate → need_info |

`run_cases.py` also runs rule checks that no database customer reaches. They
skip the model and feed `score` and `route` a hand-made customer, the guide's
C105 (credit score 670), as test input only:

| Check | Expected |
|---|---|
| Credit score 670 | refer (policy 1.3), the guide's case 4 |
| Credit score 719 | refer (last score in the refer band) |
| Credit score 720 | approve (first eligible score) |
| Credit score 640 | reject |
| Amount 20,00,000 | reject (policy 2.1) |
| Tenure 72 months | reject (policy 2.2) |
| Customer 161 with amount 0 | need_info |
| Customer 161 with tenure -12 | need_info |

## Which nodes use the model, and why only those

Only `intake` uses the model. It is the one step that has to understand messy
human text, such as "5 lakh", "3 years" or "12,00,000", and turn it into typed
fields. Every other step is a fixed bank rule: a `None` check, the EMI formula
and simple comparisons. Plain code gets those right every time, gives the same
decision for the same input, lets me point to the exact line that rejected a
case, and costs no model call. If `intake` misreads a request, the damage is
contained: the Day 1 reader never guesses, so a missing amount or tenure sends
the case to `need_info` instead of to a wrong approval.

## Differences from the guide

- Customers come live from the database (161, 162, and 999 as the missing one)
  instead of the mock C101 to C105 in `data/customers.py`, so the 6 cases use
  those customers and amounts.
- The eligible credit score is 720, not the policy's 700: 720 and above can be
  approved, 650 to 719 is referred, below 650 is rejected. So customer 161
  (725) is approved and customer 162 (701) is referred.
- The guide's single `route` is split into two conditional edges, so missing
  information is caught before scoring.
- The policy's loan amount (2.1) and tenure (2.2) limits are applied as reject
  rules. The guide's Day 4 rules do not list them, but the policy does, and
  without them a 600-month loan was approved.
- The age, income and burden limits are imported from Day 2 `tools.py`; the
  credit limits (650 reject, 720 eligible) are set in `nodes.py`, not the 715
  from Day 2.

## Model and tracing

- Chat model: `ollama:qwen3.5:9b` (local), `reasoning=False`, `temperature=0`
- Tracing: LangSmith project `langchain-week`

## One thing that surprised me

When I typed my email address instead of a loan request, the graph said
`need_info` rather than inventing an amount. The model read nothing useful,
`validate` saw the missing fields, and the routing did the rest. Because only
one step uses the model and it is told never to guess, bad input fails safely.
