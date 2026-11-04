"""Streamlit UI smoke tests (AppTest), pointed at the test DB and temp checkpoints."""

import os
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url
from streamlit.testing.v1 import AppTest
from support import MANAGER_USER
from ui_helpers import rupee

from loan_application.db import engine

pytestmark = pytest.mark.seeded
APP = str(Path(__file__).resolve().parents[1] / "day5_capstone" / "streamlit_app.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("LOAN_CHECKPOINTS_DB", str(tmp_path / "ui.db"))
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["user"] = MANAGER_USER
    return at.run()


def every_text(at) -> str:
    parts = [e.value for e in at.markdown] + [e.value for e in at.code]
    parts += [e.value for e in at.caption] + [e.value for e in at.sidebar.markdown]
    parts += [e.value for e in at.sidebar.code]
    return "\n".join(str(p) for p in parts)


def test_ui_loads_with_all_tabs(app):
    assert not app.exception
    assert [t.label for t in app.tabs] == [
        "Chat Assistant",
        "New Application",
        "Officer Inbox",
        "Case Viewer",
    ]


def test_ui_points_at_test_databases(app, tmp_path):
    assert (engine.url.database or "").endswith("_test")
    assert str(tmp_path / "ui.db") in "\n".join(e.value for e in app.sidebar.code)


def test_ui_never_shows_keys_or_db_password(app):
    shown = every_text(app)
    key = os.environ.get("LANGSMITH_API_KEY")
    if key:
        assert key not in shown
    password = make_url(os.environ["DATABASE_URL"]).password
    if password:
        assert password not in shown


def test_ui_rupee_formatter():
    assert rupee(500000) == "₹5,00,000"
    assert rupee(2500000) == "₹25,00,000"


@pytest.mark.llm
def test_ui_off_topic_declined(app):
    app.chat_input[0].set_value("What is the capital of France?").run(timeout=900)
    assert not app.exception
    replies = [m for m in app.chat_message if m.name == "assistant"]
    assert replies
    reply = replies[-1].markdown[0].value.lower()
    assert "paris" not in reply
    assert "loan" in reply
