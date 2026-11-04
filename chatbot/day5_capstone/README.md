# Day 5 – Human Approval, Memory and Tracing

## What I built

My Day 4 pre-screening graph, made ready for a real approval process. The
graph now saves its state after every step under a `thread_id` (one per case,
`case-<customer id>`), so a case can be continued later. The `refer` node no
longer decides by itself: it pauses with `interrupt()` and asks a loan officer
"Approve this loan?". The officer answers with `Command(resume=...)`, even after
the program has been closed, because cases are saved in SQLite
(`checkpoints.db`). Clear cases (approve, reject, need_info) still finish on
their own; only borderline cases wait for a human.

## How to run

From the `chatbot/` folder (so `.env` is found), with Ollama and the customer
database running:

```powershell
uv run python day5_capstone/officer_app.py             # the app: start a case, list pending cases, decide one
uv run python day5_capstone/lab1_memory.py             # Lab 1: memory on one thread
uv run python day5_capstone/lab2_interrupt.py          # Lab 2: pause at refer, then resume
uv run python day5_capstone/lab3_sqlite.py start       # Lab 3: run until the pause, then Python exits
uv run python day5_capstone/lab3_sqlite.py status      #        new process: the case is still waiting
uv run python day5_capstone/lab3_sqlite.py resume      #        new process: decide it and finish
uv run python day5_capstone/lab4_stream.py             # Lab 4: watch each step as it finishes
```

`officer_app.py` is the one command for the whole app. To start again from a
clean state, delete `day5_capstone/checkpoints.db`.

## Files

| File | What it shows |
|---|---|
| `approval_graph.py` | Day 4's graph with a new `refer` that calls `interrupt()`; `build_graph(checkpointer)`, `sqlite_graph()`, `SERDE` and `DB_PATH` |
| `lab1_memory.py` | `InMemorySaver`, `thread_id`, `get_state` and `get_state_history`: the same thread remembers, a new one is empty |
| `lab2_interrupt.py` | The first call stops at `refer` with the question; `Command(resume=...)` finishes it with the officer's answer |
| `lab3_sqlite.py` | `start` / `status` / `resume` as separate processes, all reading the same `checkpoints.db` |
| `lab4_stream.py` | `graph.stream(..., stream_mode="updates")`, printing each node's log line and the `__interrupt__` step |
| `officer_app.py` | The officer's menu: start a case, list every case waiting for a decision, approve or reject one |
| `trace_screenshot.png` | Lab 5: a LangSmith trace showing the model call and the pause |

## How the pause works

1. `score` sends a borderline case to `refer`.
2. `refer` works out the reason, then calls `interrupt({...})`. The graph saves
   itself and returns the question under `__interrupt__`. `get_state(config).next`
   is `('refer',)`.
3. Later, `graph.invoke(Command(resume={"decision": "approve"}), config)` loads the
   saved case and runs `refer` again from the top. This time `interrupt()`
   returns the officer's answer instead of pausing.
4. `refer` records the decision and the case ends. `intake`, `validate` and
   `score` do not run again.

## Results

| Lab | Case | Result |
|---|---|---|
| 1 | 161, 5 lakh for 3 years | `approve`; the log grew from 4 to 8 lines on the same thread; `case-new` was `{}` |
| 2 | 162, 2 lakh for 24 months | paused at `('refer',)` with "Approve this loan?", then finished with the typed decision |
| 3 | 162, 2 lakh for 24 months | `start` paused and exited; `status` in a new process still saw the pause; `resume` finished it as `approve`. The log shows `intake` only once |
| 4 | 162 and 161 | streamed intake → validate → score → `[PAUSED]`, then only `[refer]` after the resume; 161 streamed straight to `[approve]` |
| App | 162 and 161 | session 1: 162 waiting, 161 approved; session 2 (new process): 162 still pending, rejected by the officer, then no cases pending |

Customer 162's reason: credit score 701 is between 650 and 719 (policy 1.3).

## Lab 5: reading the trace

One paused case gives two traces in LangSmith:

- **Before the pause:** `intake` → `validate` → `score` → `refer`. The model is
  called only inside `intake` (took _fill in_ seconds). The graph paused in
  `refer` (took _fill in_ ms).
- **After the resume:** only `refer`, which proves nothing earlier ran again.

## Differences from the guide

- `sqlite_graph()` creates `SqliteSaver(sqlite3.connect(...), serde=SERDE)`
  instead of `SqliteSaver.from_conn_string(...)`, because the shortcut cannot take
  a serializer. `SERDE` allows the Day 1 `LoanEnquiry` stored in state to be
  loaded back; without it LangGraph warns, and a future version blocks it.
- The guide's `refer` reads `state["reason"]`, but in my Day 4 graph `reason` is
  set by the outcome nodes, so the new `refer` works it out with `refer_reasons`
  before pausing.
- Customers come from the database (161, 162) instead of C101 to C105, the same
  as Day 4.
- `checkpoints.db` sits next to the code (`DB_PATH`), so every script uses the
  same file whichever folder it is run from. It is in `.gitignore`.
- `officer_app.py` is an extra beyond the labs.

## Streamlit UI

A web front end for the whole Loan Assistant, with a login for customers and
managers (bank officers). Logins are the existing `users` table, checked with
the API's `authenticate_user`.

### How to run

From the `chatbot/` folder, with Docker (customer database) and Ollama running:

```powershell
uv run streamlit run day5_capstone/streamlit_app.py
```

Log in as a customer or a manager. Use a login created with
`src/loan_application/scripts/seed.py`; no passwords are stored in this folder.

### What each role sees

| Tab | Customer | Manager |
|---|---|---|
| Chat Assistant | Policy, EMI and eligibility questions; can only look up their own customer record | Any customer |
| New Application | Customer ID locked to their own; each step is shown live as the graph runs | Any customer ID |
| Officer Inbox | Hidden | Every paused case: approve or reject with a comment, recorded as decided by the manager's username |
| Case Viewer | Only their own cases | Any case: decision card, log, next node, history table, Mermaid diagram |

The sidebar shows the logged-in user, a Log out button, whether LangSmith
tracing is on and the project name (never the key), the checkpoints file in
use, and a New chat button.

### Files

| File | What it does |
|---|---|
| `streamlit_app.py` | The UI only: login page, sidebar, the four tabs |
| `accounts.py` | Login against the `users` table, `UserContext`, and who may see which customer |
| `cases.py` | Case logic for the UI: start (streamed), list waiting cases, decide, history, ownership |
| `policy_agent.py` | `create_agent` with `search_policy`, `emi_calculator`, `percentage_calculator`, `get_customer` and `check_eligibility`, and the chat rules as the system prompt |
| `ui_helpers.py` | Rupee formatting (₹5,00,000), the decision card, step lines, the waiting box |
| `tests/test_logic.py` | Routing, inbox, restart, login, access and chat tests |
| `tests/test_ui.py` | `AppTest` smoke tests of the login page, tabs, sidebar, inbox and viewer |

### Which nodes use the model

Only `intake` in the graph (reading the customer's message) and the Chat
Assistant agent. Every routing rule, the EMI, the eligibility checks and the
officer's decision are plain code, so the same input always gives the same,
explainable decision.

### Design notes

- The agent is built once (`st.cache_resource`) but every call passes the
  logged-in `UserContext` as runtime context. The `get_customer` tool checks
  that context, so one browser session can never see another customer's data.
  Day 2's module-level `current_user` is not used, because Streamlit serves
  every session from one Python process.
- `percentage_calculator` is a fifth tool beyond the four in the spec: the
  chat rules say every number must come from a tool, and the processing fee
  (1.5% of the amount) is a calculation.
- The officer's comment and username are saved in state (`officer_comment`,
  `decided_by`) through the resume value, so they survive a restart too.
- The app and `officer_app.py` use the same `checkpoints.db`, so a case started
  in the CLI appears in the Officer Inbox.

### Tests

```powershell
uv run pytest chatbot/day5_capstone/tests -m "not llm"   # fast: Postgres only, no model
uv run pytest chatbot/day5_capstone/tests -m llm         # chat and model tests, needs Ollama (slow)
```

The routing tests write a pre-filled enquiry into state as if `intake` had run,
so they need no model and always give the same result. The login tests create
a temporary customer and two temporary logins, and delete them afterwards.

### Screenshots to add

- `screenshots/login.png`: the login page
- `screenshots/chat.png`: a policy answer with the Tools used expander open
- `screenshots/application.png`: a New Application run paused at refer
- `screenshots/inbox.png`: the Officer Inbox with a case
- `screenshots/viewer.png`: the Case Viewer with the history table

## Model and tracing

- Chat model: `ollama:qwen3.5:9b` (local), used only in `intake`
- Tracing: LangSmith project `langchain-week`

## One thing that surprised me

`interrupt()` does not continue from the middle of the node. When the officer
answers, the whole `refer` node runs again from its first line, and only then
does `interrupt()` hand back the answer. So any code before `interrupt()` runs
twice, and it has to be safe to repeat. Mine only works out the reason, so that
is fine.
