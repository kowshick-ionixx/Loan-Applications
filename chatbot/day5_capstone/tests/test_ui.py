import os

import cases
import pytest
from accounts import CUSTOMER, UserContext
from approval_graph import sqlite_graph
from conftest import DAY5, MANAGER_USER
from streamlit.testing.v1 import AppTest

APP = str(DAY5 / "streamlit_app.py")
MANAGER_TABS = ["Chat Assistant", "New Application", "Officer Inbox", "Case Viewer"]
CUSTOMER_TABS = ["Chat Assistant", "New Application", "Case Viewer"]


@pytest.fixture
def db_file(tmp_path, monkeypatch):
    """Point the app at a temporary checkpoints file."""
    path = tmp_path / "ui.db"
    monkeypatch.setenv("LOAN_CHECKPOINTS_DB", str(path))
    return path


def app_as(user=None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    if user is not None:
        at.session_state["user"] = user
    return at.run()


def tab_labels(at) -> list[str]:
    return [tab.label for tab in at.tabs]


def button(at, label):
    return next(b for b in at.button if b.label == label)


def all_text(at) -> str:
    parts = [e.value for e in at.markdown] + [e.value for e in at.code]
    parts += [e.value for e in at.caption] + [str(e.value) for e in at.text_input]
    return "\n".join(str(p) for p in parts)


def log_in(at, role, username, password):
    at.radio[0].set_value(role)
    at.text_input[0].set_value(username)
    at.text_input[1].set_value(password)
    return button(at, "Log in").click().run()


# ---------- D1: the app loads ----------


def test_d1_login_page_loads(db_file):
    at = app_as()
    assert not at.exception
    assert [s.value for s in at.subheader] == ["Log in"]
    assert at.tabs == [] or len(at.tabs) == 0


def test_d1_manager_sees_all_four_tabs(db_file):
    at = app_as(MANAGER_USER)
    assert not at.exception
    assert tab_labels(at) == MANAGER_TABS


# ---------- D3: sidebar ----------


def test_d3_sidebar_tracing_status_and_no_api_key(db_file):
    at = app_as(MANAGER_USER)
    sidebar = "\n".join(e.value for e in at.sidebar.markdown)
    assert "LANGSMITH_TRACING" in sidebar
    assert "Project:" in sidebar
    assert str(db_file) in "\n".join(e.value for e in at.sidebar.code)
    key = os.environ.get("LANGSMITH_API_KEY")
    if key:
        assert key not in all_text(at)


# ---------- L: login page ----------


def test_l1_wrong_password_shows_error_and_no_tabs(db_file, accounts_in_db):
    at = log_in(app_as(), "Customer", accounts_in_db["customer"], "wrong")
    assert not at.exception
    assert "Invalid username, password or role" in at.error[0].value
    assert len(at.tabs) == 0


def test_l2_customer_login_hides_inbox_and_locks_customer_id(db_file, accounts_in_db):
    at = log_in(
        app_as(), "Customer", accounts_in_db["customer"], accounts_in_db["password"]
    )
    assert not at.exception
    assert tab_labels(at) == CUSTOMER_TABS
    customer_box = next(t for t in at.text_input if t.label == "Customer ID")
    assert customer_box.value == str(accounts_in_db["customer_id"])
    assert customer_box.disabled


def test_l4_manager_login_shows_all_tabs(db_file, accounts_in_db):
    at = log_in(
        app_as(), "Manager", accounts_in_db["manager"], accounts_in_db["password"]
    )
    assert not at.exception
    assert tab_labels(at) == MANAGER_TABS


def test_l6_logout_returns_to_login(db_file):
    at = app_as(MANAGER_USER)
    next(b for b in at.sidebar.button if b.label == "Log out").click().run()
    assert not at.exception
    assert [s.value for s in at.subheader] == ["Log in"]
    assert len(at.tabs) == 0


# ---------- B7, C and L5 through the UI ----------


def test_b7_empty_message_is_a_friendly_validation(db_file):
    at = app_as(MANAGER_USER)
    next(t for t in at.text_input if t.label == "Customer ID").set_value("161")
    button(at, "Run pre-screening").click().run()
    assert not at.exception
    assert "Please enter the customer ID and the customer's message." in [
        w.value for w in at.warning
    ]


def test_c_inbox_approve_removes_the_case(db_file, prefilled):
    graph = sqlite_graph(db_file)
    prefilled(graph, "ui-refer", "162", 200000, 24)
    graph.checkpointer.conn.close()

    at = app_as(MANAGER_USER)
    assert "ui-refer" in all_text(at)
    at.text_input(key="comment-ui-refer").set_value("Verified salary")
    at.button(key="approve-ui-refer").click().run()
    assert not at.exception
    assert "Decided `ui-refer`" in at.success[0].value
    assert "No cases are waiting for a decision." in [i.value for i in at.info]

    graph = sqlite_graph(db_file)
    values = cases.case_values(graph, "ui-refer")
    graph.checkpointer.conn.close()
    assert values["decision"] == "approve"
    assert values["decided_by"] == MANAGER_USER.username
    assert values["officer_comment"] == "Verified salary"


def test_c7_case_viewer_unknown_case(db_file):
    at = app_as(MANAGER_USER)
    at.text_input(key="viewer_thread").set_value("no-such-case").run()
    assert not at.exception
    assert "No case found with ID no-such-case." in [w.value for w in at.warning]


def test_l5_customer_cannot_view_another_customers_case(db_file, prefilled):
    graph = sqlite_graph(db_file)
    prefilled(graph, "agilan-case", "162", 200000, 24)
    graph.checkpointer.conn.close()

    at = app_as(UserContext("vetri", CUSTOMER, 161))
    at.text_input(key="viewer_thread").set_value("agilan-case").run()
    assert not at.exception
    assert "No case found with ID agilan-case." in [w.value for w in at.warning]


# ---------- D2: chat (real model) ----------


@pytest.mark.llm
def test_d2_chat_declines_off_topic(db_file):
    at = app_as(MANAGER_USER)
    at.chat_input[0].set_value("What is the capital of France?").run(timeout=600)
    assert not at.exception
    replies = [m for m in at.chat_message if m.name == "assistant"]
    assert replies
    assert "loan" in replies[-1].markdown[0].value.lower()
