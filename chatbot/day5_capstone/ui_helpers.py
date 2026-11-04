import os

import streamlit as st

BADGES = {
    "approve": ("APPROVE", "green"),
    "refer": ("REFER", "orange"),
    "reject": ("REJECT", "red"),
    "need_info": ("NEED_INFO", "gray"),
}


def rupee(amount, decimals: int = 0) -> str:
    """Indian grouping: 500000 -> ₹5,00,000; 16369.857, 2 -> ₹16,369.86."""
    if amount is None:
        return "-"
    sign = "-" if amount < 0 else ""
    whole, _, fraction = f"{abs(amount):.{decimals}f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        groups.insert(0, head)
        whole = ",".join(groups) + "," + tail
    return f"{sign}₹{whole}" + (f".{fraction}" if fraction else "")


def decision_card(values: dict, rate_percent: float) -> dict:
    """The fields of a decision card, from a case's saved state."""
    decision = values.get("decision") or "refer"
    label, colour = BADGES.get(decision, (decision.upper(), "gray"))
    customer = values.get("customer") or {}
    enquiry = values.get("enquiry")
    name = customer.get("name") or "unknown"
    emi = values.get("emi")
    return {
        "badge": label,
        "colour": colour,
        "customer": f"{name} ({values.get('customer_id', '-')})",
        "amount": rupee(enquiry.amount) if enquiry else "-",
        "tenure": (
            f"{enquiry.tenure_months} months"
            if enquiry and enquiry.tenure_months
            else "-"
        ),
        "emi": f"{rupee(emi, 2)} at {rate_percent}%" if emi else "-",
        "reason": values.get("reason", "-"),
        "failed_rules": values.get("failed_rules") or [],
        "path": " → ".join(values.get("log", [])),
        "decided_by": values.get("decided_by"),
        "comment": values.get("officer_comment"),
    }


def render_decision_card(values: dict, rate_percent: float) -> None:
    card = decision_card(values, rate_percent)
    with st.container(border=True):
        st.markdown(f"### :{card['colour']}-background[{card['badge']}]")
        st.markdown(f"**Customer:** {card['customer']}")
        left, middle, right = st.columns(3)
        left.metric("Amount", card["amount"])
        middle.metric("Tenure", card["tenure"])
        right.metric("EMI", card["emi"])
        st.markdown(f"**Reason:** {card['reason']}")
        if card["failed_rules"]:
            st.markdown(
                "**Failed rules:**\n"
                + "\n".join(f"- {r}" for r in card["failed_rules"])
            )
        st.caption(f"Path: {card['path']}")
        if card["decided_by"]:
            note = f"Decided by officer **{card['decided_by']}**"
            if card["comment"]:
                note += f": “{card['comment']}”"
            st.info(note)


def describe_update(node: str, update: dict) -> str:
    """One line for a finished step: the node, its log line, and the fields it changed."""
    changed = ", ".join(key for key in update if key != "log")
    line = update.get("log", [""])[-1]
    return f"**{node}**: {line}" + (f"  \n_changed: {changed}_" if changed else "")


def render_waiting(thread_id: str, payload: dict) -> None:
    with st.container(border=True):
        st.markdown(
            f"### :{BADGES['refer'][1]}-background[Waiting for officer approval]"
        )
        st.markdown(f"**Case:** `{thread_id}`")
        st.markdown(f"**Question:** {payload['question']}")
        st.markdown(f"**Customer:** {payload['customer']}")
        st.markdown(f"**Reason:** {payload['reason']}")


def tracing_status() -> tuple[bool, str]:
    """Whether LangSmith tracing is on, and the project name. Never the key."""
    tracing = os.environ.get("LANGSMITH_TRACING", "").lower() == "true"
    return tracing, os.environ.get("LANGSMITH_PROJECT", "default")
