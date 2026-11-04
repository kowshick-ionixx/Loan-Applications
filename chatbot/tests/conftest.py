"""End-to-end test setup for the Loan Assistant (Day 1 to Day 5).

Before any app module is imported, DATABASE_URL is pointed at the isolated
test database (app_db_test), or, with RUN_LIVE_TESTS=1, at the dev database
through a read-only transaction. The app reads DATABASE_URL from the
environment first, so no app code is changed.
"""

import os
import sys
import uuid
from pathlib import Path

import pytest
from dotenv import dotenv_values, load_dotenv
from sqlalchemy.engine import make_url

TESTS = Path(__file__).resolve().parent
CHATBOT = TESTS.parent
ROOT = CHATBOT.parent
LIVE = os.environ.get("RUN_LIVE_TESTS") == "1"
DAYS = ["day5_capstone", "day4_langgraph", "day3_rag", "day2_agents", "day1_langchain"]

load_dotenv(CHATBOT / ".env")  # LangSmith settings, the same file the app uses

DEV_URL = make_url(
    os.environ.get("DATABASE_URL") or dotenv_values(ROOT / ".env")["DATABASE_URL"]
)
TEST_URL = make_url(
    os.environ.get("TEST_DATABASE_URL") or DEV_URL.set(database="app_db_test")
)
if not (TEST_URL.database or "").endswith("_test"):
    pytest.exit("Refusing to run: the test database name must end with _test", 1)
READ_ONLY_DEV_URL = DEV_URL.update_query_dict(
    {"options": "-c default_transaction_read_only=on"}
)
APP_URL = READ_ONLY_DEV_URL if LIVE else TEST_URL
os.environ["DATABASE_URL"] = APP_URL.render_as_string(hide_password=False)


def add_app_paths() -> None:
    for folder in reversed(DAYS):
        sys.path.insert(0, str(CHATBOT / folder))
    sys.path.insert(0, str(TESTS))


add_app_paths()

import factories
import nodes
import tools
from approval_graph import sqlite_graph
from enquiry_reader import LoanEnquiry
from support import MANAGER_USER

from loan_application.db import engine


def load_thresholds() -> dict:
    """Every rule value and the rate, from the constants the chatbot uses."""
    return {
        "min_age": tools.MIN_AGE,
        "max_age": tools.MAX_AGE,
        "min_income": tools.MIN_INCOME,
        "burden_pct": tools.MAX_BURDEN_PERCENT,
        "agent_min_credit": tools.MIN_CREDIT_SCORE,
        "min_credit": nodes.ELIGIBLE_SCORE,
        "reject_below": nodes.MIN_CREDIT_SCORE,
        "refer_from": nodes.MIN_CREDIT_SCORE,
        "high_value_limit": nodes.REFER_AMOUNT,
        "min_amount": nodes.MIN_AMOUNT,
        "max_amount": nodes.MAX_AMOUNT,
        "min_tenure": nodes.MIN_TENURE,
        "max_tenure": nodes.MAX_TENURE,
        "rate": nodes.RATE_PERCENT,
    }


THRESHOLDS = load_thresholds()


def pytest_report_header(config):
    lines = [
        f"app database: {APP_URL.database} ({'LIVE, read-only' if LIVE else 'seeded'})"
    ]
    lines.append("thresholds: " + ", ".join(f"{k}={v}" for k, v in THRESHOLDS.items()))
    return lines


def pytest_collection_modifyitems(config, items):
    """Live tests only with RUN_LIVE_TESTS=1; seeded tests only without it."""
    for item in items:
        is_live = "live" in item.keywords
        if is_live and not LIVE:
            item.add_marker(pytest.mark.skip(reason="set RUN_LIVE_TESTS=1 to run"))
        elif LIVE and not is_live:
            item.add_marker(
                pytest.mark.skip(reason="seeded test; LIVE run is read-only")
            )


# ---------- the isolated test database ----------


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    """Fresh schema from the app's own Alembic migrations, once per session."""
    if LIVE:
        yield
        return
    from alembic.config import Config
    from sqlalchemy import text

    from alembic import command

    assert (engine.url.database or "").endswith("_test")
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    yield


@pytest.fixture(autouse=True)
def clean_db():
    """Every seeded test starts with empty tables."""
    if LIVE:
        yield
        return
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE customers, loans, users RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture(scope="session")
def thresholds():
    return THRESHOLDS


@pytest.fixture
def factory(thresholds):
    return factories.CustomerFactory(thresholds)


# ---------- graph, checkpointer, reader ----------


@pytest.fixture
def graph(tmp_path):
    """The approval graph on its own temporary checkpoints file."""
    graph = sqlite_graph(tmp_path / "checkpoints.db")
    yield graph
    graph.checkpointer.conn.close()


@pytest.fixture
def thread_id():
    return f"t-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def fake_reader(monkeypatch):
    """Replace the model in intake with a fixed enquiry: the whole graph still
    runs (intake included) but needs no model and always gives the same input."""

    def use(amount, tenure_months):
        missing = [
            name
            for name, value in (("amount", amount), ("tenure_months", tenure_months))
            if value is None
        ]
        enquiry = LoanEnquiry(
            amount=amount,
            tenure_months=tenure_months,
            purpose="test",
            confidence="medium" if missing else "high",
            missing_fields=missing,
        )
        monkeypatch.setattr(nodes, "read_enquiry", lambda text: enquiry)

    return use


@pytest.fixture
def run_case():
    """Run one application through the graph. Returns (stream events, snapshot)."""
    import cases

    def run(graph, thread_id, customer_id, email="(test message)"):
        events = list(cases.stream_case(graph, thread_id, str(customer_id), email))
        return events, graph.get_state(cases.thread_config(thread_id))

    return run


# ---------- model, index, agent ----------


@pytest.fixture(scope="session")
def agent():
    from policy_agent import build_agent

    return build_agent()


@pytest.fixture
def chat(agent):
    """Ask the chat agent one question as a manager.
    Returns (answer, tool names in order, all messages)."""
    from policy_agent import answer_text, ask

    def send(question, user=MANAGER_USER):
        history, calls = ask(agent, [], question, user)
        return answer_text(history), [c["name"] for c in calls], history

    return send


@pytest.fixture(scope="session")
def policy_text():
    import policy_index

    return Path(policy_index.POLICY_FILE).read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def index():
    import policy_index

    return policy_index.build_index()
