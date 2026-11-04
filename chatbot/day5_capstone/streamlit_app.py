import logging
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dotenv import load_dotenv

load_dotenv(HERE.parent / ".env")

import cases
import streamlit as st
from accounts import CUSTOMER, MANAGER, login
from approval_graph import DB_PATH, sqlite_graph
from ui_helpers import (
    describe_update,
    render_decision_card,
    render_waiting,
    rupee,
    tracing_status,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("loan_assistant")

MAX_LOGIN_ATTEMPTS = 3
# Tests point this at a temporary file; the app and officer_app.py share DB_PATH.
DB_FILE = Path(os.environ.get("LOAN_CHECKPOINTS_DB") or DB_PATH)


@st.cache_resource
def get_graph(db_file: str):
    return sqlite_graph(Path(db_file))


@st.cache_resource(show_spinner="Loading the loan policy and the assistant...")
def get_agent():
    from policy_agent import build_agent

    return build_agent()


def graph():
    return get_graph(str(DB_FILE))


def friendly_error(action: str) -> None:
    """Log the full error to the console; show the user a short message."""
    log.exception("%s failed", action)
    st.error(
        f"Sorry, {action} failed. Please try again. If it keeps happening, "
        "check that Ollama and the customer database are running."
    )


def init_session() -> None:
    defaults = {
        "user": None,
        "login_attempts": 0,
        "chat": [],
        "agent_history": [],
        "last_application": None,
        "last_decided": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def login_page() -> None:
    st.title("Loan Assistant")
    st.subheader("Log in")
    if st.session_state.login_attempts >= MAX_LOGIN_ATTEMPTS:
        st.error("Too many failed attempts. Reload the page to try again.")
        return
    with st.form("login"):
        role_label = st.radio("I am a", ["Customer", "Manager"], horizontal=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary")
    if not submitted:
        return
    role = MANAGER if role_label == "Manager" else CUSTOMER
    try:
        user, error = login(username, password, role)
    except Exception:  # noqa: BLE001
        friendly_error("logging in")
        return
    if user is None:
        st.session_state.login_attempts += 1
        st.error(f"{error} ({st.session_state.login_attempts}/{MAX_LOGIN_ATTEMPTS})")
        return
    st.session_state.user = user
    st.session_state.login_attempts = 0
    st.rerun()


def sidebar(user) -> None:
    with st.sidebar:
        st.title("Loan Assistant")
        who = "Manager" if user.is_manager else f"Customer {user.customer_id}"
        st.markdown(f"Logged in as **{user.username}** ({who})")
        if st.button("Log out"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        tracing, project = tracing_status()
        st.markdown("**LangSmith tracing**")
        st.markdown(f"LANGSMITH_TRACING: `{'true' if tracing else 'false'}`")
        st.markdown(f"Project: `{project}`")
        st.markdown("**Checkpoints database**")
        st.code(str(DB_FILE), language=None)
        if st.button("New chat"):
            st.session_state.chat = []
            st.session_state.agent_history = []
            st.rerun()


def chat_tab(user) -> None:
    from policy_agent import answer_text, ask

    for turn in st.session_state.chat:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn.get("tools"):
                with st.expander("Tools used"):
                    for call in turn["tools"]:
                        st.markdown(f"`{call['name']}` {call['args']}")

    question = st.chat_input("Ask about loans, EMIs, eligibility or the policy")
    if not question:
        return
    st.session_state.chat.append({"role": "user", "content": question})
    try:
        with st.spinner("Thinking..."):
            history, calls = ask(
                get_agent(), st.session_state.agent_history, question, user
            )
    except Exception:  # noqa: BLE001
        st.session_state.chat.pop()
        friendly_error("answering your question")
        return
    st.session_state.agent_history = history
    st.session_state.chat.append(
        {"role": "assistant", "content": answer_text(history), "tools": calls}
    )
    st.rerun()


def show_case(thread_id: str) -> None:
    """The decision card of a case, or the waiting box if it is paused."""
    snapshot = graph().get_state(cases.thread_config(thread_id))
    if snapshot.interrupts:
        render_waiting(thread_id, snapshot.interrupts[0].value)
    else:
        render_decision_card(snapshot.values, cases.RATE_PERCENT)


def application_tab(user) -> None:
    st.subheader("New application")
    with st.form("application"):
        if user.is_manager:
            customer_id = st.text_input("Customer ID", placeholder="e.g. 161")
        else:
            customer_id = str(user.customer_id)
            st.text_input("Customer ID", value=customer_id, disabled=True)
        email = st.text_area(
            "Customer message",
            placeholder="e.g. I need 5 lakh for 3 years to renovate my house.",
        )
        thread_id = st.text_input(
            "Case ID (optional)", placeholder="empty: case-YYYYMMDD-HHMMSS"
        )
        run = st.form_submit_button("Run pre-screening", type="primary")

    if run:
        run_application(customer_id, email, thread_id.strip() or cases.new_thread_id())
    elif st.session_state.last_application:
        st.caption(f"Last case: `{st.session_state.last_application}`")
        show_case(st.session_state.last_application)


def run_application(customer_id: str, email: str, thread_id: str) -> None:
    if not customer_id.strip() or not email.strip():
        st.warning("Please enter the customer ID and the customer's message.")
        return
    if cases.case_values(graph(), thread_id):
        st.error(
            f"Case ID {thread_id} is already in use. Leave it empty for a new one."
        )
        return
    try:
        with st.status(f"Pre-screening {thread_id}", expanded=True) as status:
            paused = False
            for node, update in cases.stream_case(
                graph(), thread_id, customer_id, email
            ):
                if node == "__interrupt__":
                    paused = True
                    st.markdown("**paused**: waiting for an officer")
                else:
                    st.markdown(describe_update(node, update))
            status.update(
                label=f"{thread_id}: {'paused at refer' if paused else 'finished'}",
                state="complete",
            )
    except Exception:  # noqa: BLE001
        friendly_error("pre-screening")
        return
    st.session_state.last_application = thread_id
    show_case(thread_id)


def inbox_tab(user) -> None:
    left, right = st.columns([4, 1])
    left.subheader("Officer inbox")
    if right.button("Refresh"):
        st.rerun()

    if st.session_state.last_decided:
        st.success(f"Decided `{st.session_state.last_decided}`")
        show_case(st.session_state.last_decided)

    try:
        waiting = cases.waiting_cases(graph())
    except Exception:  # noqa: BLE001
        friendly_error("loading the inbox")
        return
    if not waiting:
        st.info("No cases are waiting for a decision.")
        return

    for thread_id in waiting:
        case = cases.waiting_summary(graph(), thread_id)
        with st.container(border=True):
            st.markdown(f"#### `{thread_id}`")
            name, amount, tenure, emi = st.columns(4)
            name.metric("Customer", f"{case['name'] or '-'} ({case['customer_id']})")
            amount.metric("Amount", rupee_or_dash(case["amount"]))
            tenure.metric(
                "Tenure",
                f"{case['tenure_months']} months" if case["tenure_months"] else "-",
            )
            emi.metric("EMI", rupee_or_dash(case["emi"], 2))
            st.markdown(f"**Referred because:** {case['reason']}")
            st.markdown(f"**Question:** {case['question']}")
            comment = st.text_input("Comment (optional)", key=f"comment-{thread_id}")
            approve, reject = st.columns(2)
            if approve.button("Approve", key=f"approve-{thread_id}", type="primary"):
                decide(user, thread_id, "approve", comment)
            if reject.button("Reject", key=f"reject-{thread_id}"):
                decide(user, thread_id, "reject", comment)


def rupee_or_dash(amount, decimals: int = 0) -> str:
    return rupee(amount, decimals) if amount else "-"


def decide(user, thread_id: str, decision: str, comment: str) -> None:
    try:
        cases.decide(graph(), thread_id, decision, user.username, comment)
    except Exception:  # noqa: BLE001
        friendly_error(f"recording the decision for {thread_id}")
        return
    st.session_state.last_decided = thread_id
    st.rerun()


def viewer_tab(user) -> None:
    st.subheader("Case viewer")
    if not user.is_manager:
        mine = cases.visible_cases(graph(), user)
        st.caption("Your cases: " + (", ".join(f"`{t}`" for t in mine) or "none yet"))
    thread_id = st.text_input("Case ID", key="viewer_thread").strip()
    if thread_id:
        show_case_details(user, thread_id)
    with st.expander("Graph diagram (Mermaid)"):
        st.code(graph().get_graph().draw_mermaid(), language="mermaid")


def show_case_details(user, thread_id: str) -> None:
    try:
        snapshot = graph().get_state(cases.thread_config(thread_id))
    except Exception:  # noqa: BLE001
        friendly_error("loading the case")
        return
    values = snapshot.values
    if not cases.can_view(user, values):
        st.warning(f"No case found with ID {thread_id}.")
        return
    show_case(thread_id)
    st.markdown("**Log**")
    st.markdown(
        "\n".join(f"{i}. {line}" for i, line in enumerate(values.get("log", []), 1))
    )
    st.markdown(f"**Next node:** {', '.join(snapshot.next) or 'none (finished)'}")
    st.markdown("**History**")
    st.dataframe(cases.history_rows(graph(), thread_id), hide_index=True)
    with st.expander("State values"):
        st.json(
            {
                key: value.model_dump() if hasattr(value, "model_dump") else value
                for key, value in values.items()
            }
        )


def main() -> None:
    st.set_page_config(page_title="Loan Assistant", page_icon="🏦", layout="wide")
    init_session()
    user = st.session_state.user
    if user is None:
        login_page()
        st.stop()

    sidebar(user)
    st.title("Loan Assistant")
    names = ["Chat Assistant", "New Application", "Case Viewer"]
    pages = [chat_tab, application_tab, viewer_tab]
    if user.is_manager:
        names.insert(2, "Officer Inbox")
        pages.insert(2, inbox_tab)
    for tab, page in zip(st.tabs(names), pages, strict=True):
        with tab:
            page(user)


main()
