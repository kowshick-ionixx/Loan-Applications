import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "day4_langgraph"))

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from nodes import approve, intake, need_info, refer_reasons, reject, score, validate
from prescreen_graph import after_validate, route
from state import LoanState

# Lets checkpointers load the Day 1 LoanEnquiry stored in state.
SERDE = JsonPlusSerializer(allowed_msgpack_modules=[("enquiry_reader", "LoanEnquiry")])
DB_PATH = Path(__file__).resolve().parent / "checkpoints.db"


class ApprovalState(LoanState, total=False):
    """Thursday's state plus who decided a referred case and their comment."""

    decided_by: str
    officer_comment: str


def refer(state: ApprovalState):
    """Pause for a loan officer, then record their approve or reject decision.

    The resume value is {"decision": ...}, optionally with "comment" and "officer".
    """
    reason = "Referred for review: " + "; ".join(refer_reasons(state)) + "."
    answer = interrupt(
        {
            "question": "Approve this loan?",
            "customer": state["customer_id"],
            "reason": reason,
        }
    )
    decision = answer["decision"]
    comment = answer.get("comment", "").strip()
    officer = answer.get("officer", "").strip() or "officer"
    final_reason = f"{reason} Officer decided: {decision}."
    if comment:
        final_reason += f" Comment: {comment}"
    return {
        "decision": decision,
        "reason": final_reason,
        "decided_by": officer,
        "officer_comment": comment,
        "log": [f"refer: human decided {decision}"],
    }


def build_graph(checkpointer):
    """Thursday's pre-screening graph, with refer pausing for a human."""
    builder = StateGraph(ApprovalState)
    builder.add_node("intake", intake)
    builder.add_node("validate", validate)
    builder.add_node("score", score)
    builder.add_node("approve", approve)
    builder.add_node("refer", refer)
    builder.add_node("reject", reject)
    builder.add_node("need_info", need_info)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "validate")
    builder.add_conditional_edges(
        "validate", after_validate, {"score": "score", "need_info": "need_info"}
    )
    builder.add_conditional_edges(
        "score", route, {"approve": "approve", "refer": "refer", "reject": "reject"}
    )
    for outcome in ("approve", "refer", "reject", "need_info"):
        builder.add_edge(outcome, END)

    return builder.compile(checkpointer=checkpointer)


def sqlite_graph(db_path: Path = DB_PATH):
    """The approval graph saving to checkpoints.db, so cases survive a restart."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return build_graph(SqliteSaver(conn, serde=SERDE))
