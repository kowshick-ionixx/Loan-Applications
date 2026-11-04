"""Day 5: memory, interrupt, stream, restart (seeded test DB, temp checkpoints)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import cases
import factories
import pytest
from langgraph.types import Command

pytestmark = pytest.mark.seeded
TESTS = Path(__file__).resolve().parent


def normal_loan(t):
    return t["min_amount"] * 6, 36


def high_value(t):
    return t["high_value_limit"] + t["min_amount"], 60


def paused_case(graph, thread_id, run_case, fake_reader, seeded, amount, tenure):
    fake_reader(amount, tenure)
    events, snapshot = run_case(graph, thread_id, seeded.id)
    assert snapshot.next == ("refer",)
    return events, snapshot


def test_d5_1_saved_decision(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    fake_reader(*normal_loan(thresholds))
    run_case(graph, thread_id, factory.eligible().id)
    assert cases.case_values(graph, thread_id)["decision"] == "approve"


def test_d5_2_new_thread_is_empty(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    fake_reader(*normal_loan(thresholds))
    run_case(graph, thread_id, factory.eligible().id)
    assert cases.case_values(graph, thread_id + "-other") == {}


def test_d5_3_high_value_pauses_with_payload(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    seeded = factory.eligible()
    events, snapshot = paused_case(
        graph, thread_id, run_case, fake_reader, seeded, *high_value(thresholds)
    )
    nodes_run = [node for node, _ in events]
    assert "__interrupt__" in nodes_run
    payload = dict(events)["__interrupt__"]
    assert payload["question"]
    assert payload["customer"] == str(seeded.id)
    assert payload["reason"]
    assert snapshot.values.get("decision") is None


def test_d5_4_resume_approve(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    paused_case(
        graph,
        thread_id,
        run_case,
        fake_reader,
        factory.eligible(),
        *high_value(thresholds),
    )
    graph.invoke(
        Command(resume={"decision": "approve"}), cases.thread_config(thread_id)
    )
    values = cases.case_values(graph, thread_id)
    assert values["decision"] == "approve"
    assert values["log"][-1] == "refer: human decided approve"


def test_d5_5_low_credit_resume_reject(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    paused_case(
        graph,
        thread_id,
        run_case,
        fake_reader,
        factory.low_credit_refer(),
        *normal_loan(thresholds),
    )
    graph.invoke(Command(resume={"decision": "reject"}), cases.thread_config(thread_id))
    assert cases.case_values(graph, thread_id)["decision"] == "reject"


def test_d5_6_stream_approve_order(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    fake_reader(*normal_loan(thresholds))
    events, _ = run_case(graph, thread_id, factory.eligible().id)
    assert [node for node, _ in events] == ["intake", "validate", "score", "approve"]


def test_d5_7_stream_refer_ends_with_interrupt(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    events, _ = paused_case(
        graph,
        thread_id,
        run_case,
        fake_reader,
        factory.low_credit_refer(),
        *normal_loan(thresholds),
    )
    assert events[-1][0] == "__interrupt__"


def run_helper(script, *args):
    result = subprocess.run(
        [sys.executable, str(TESTS / "helpers" / script), *map(str, args)],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=600,
        check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
    assert (
        lines
    ), f"{script} printed no result.\nstdout:{result.stdout}\nstderr:{result.stderr}"
    return result.returncode, json.loads(lines[-1])


def test_d5_8_restart_in_new_processes(tmp_path, thread_id, thresholds, factory):
    db_file = tmp_path / "restart.db"
    seeded = factory.low_credit_refer()
    amount, tenure = normal_loan(thresholds)

    code, started = run_helper(
        "restart_start.py",
        db_file,
        thread_id,
        seeded.id,
        "--amount",
        amount,
        "--tenure",
        tenure,
    )
    assert code == 0
    assert started["next"] == ["refer"]  # that process has now exited

    code, finished = run_helper("restart_resume.py", db_file, thread_id, "approve")
    assert code == 0
    assert finished["decision"] == "approve"
    steps = [line.split(":")[0] for line in finished["log"]]
    for node in ("intake", "validate", "score"):
        assert steps.count(node) == 1, f"{node} ran again after the restart"


def test_d5_9_data_change_during_pause(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    """Documents the behaviour: the resume works on the saved snapshot. The
    customer's new credit score is NOT re-read, because refer does not re-check."""
    seeded = factory.low_credit_refer()
    paused_case(
        graph, thread_id, run_case, fake_reader, seeded, *normal_loan(thresholds)
    )
    factories.set_credit_score(seeded.id, thresholds["min_credit"] + 50)
    values = cases.decide(graph, thread_id, "approve", "test-manager")
    assert values["customer"]["credit_score"] == seeded.credit_score
    assert f"credit score {seeded.credit_score}" in values["reason"]
    print(
        "FINDING (D5-9): resume used the saved snapshot; the credit score changed "
        f"from {seeded.credit_score} to {thresholds['min_credit'] + 50} during the "
        "pause and the decision did not see it."
    )


def test_d5_10_resume_unknown_thread(graph):
    with pytest.raises(ValueError, match="not waiting for a decision"):
        cases.decide(graph, "no-such-thread", "approve", "test-manager")
    assert cases.case_values(graph, "no-such-thread") == {}


def test_d5_11_two_paused_cases_are_independent(
    graph, run_case, fake_reader, thresholds, factory
):
    amount, tenure = normal_loan(thresholds)
    first, second = factory.low_credit_refer(), factory.low_credit_refer()
    paused_case(graph, "case-a", run_case, fake_reader, first, amount, tenure)
    paused_case(graph, "case-b", run_case, fake_reader, second, amount, tenure)
    before = cases.case_values(graph, "case-b")
    cases.decide(graph, "case-a", "approve", "test-manager")
    assert cases.waiting_cases(graph) == ["case-b"]
    assert cases.case_values(graph, "case-b") == before


def test_d5_12_history_is_ordered(
    graph, thread_id, run_case, fake_reader, thresholds, factory
):
    fake_reader(*normal_loan(thresholds))
    run_case(graph, thread_id, factory.eligible().id)
    steps = [row["step"] for row in cases.history_rows(graph, thread_id)]
    assert len(steps) >= 5
    assert steps == sorted(steps)


def test_d5_13_tracing_on_and_key_never_shown():
    from ui_helpers import tracing_status

    assert os.environ.get("LANGSMITH_TRACING") == "true"
    tracing, project = tracing_status()
    assert tracing
    assert project and project != "default"
    key = os.environ.get("LANGSMITH_API_KEY", "")
    if key:
        assert key not in repr(tracing_status())
