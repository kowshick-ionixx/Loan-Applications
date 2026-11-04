"""LIVE mode (RUN_LIVE_TESTS=1): read-only checks against the dev database.

The app's DATABASE_URL carries `default_transaction_read_only=on`, so Postgres
itself refuses any write. Reports show only the customer id and the fields an
assertion needs, never a full record.
"""

import os
from datetime import date, datetime

import oracle
import pytest
from loan_agent import get_customer
from sqlalchemy import text

from loan_application.db import engine

pytestmark = pytest.mark.live
SAMPLE_N = int(os.environ.get("LIVE_SAMPLE_N", "10"))

ROWS_SQL = """
SELECT c.id, c.date_of_birth, c.monthly_income, c.credit_score,
       COALESCE((SELECT SUM(l.emi) FROM loans l
                 WHERE l.customer_id = c.id AND l.status = 'APPROVED'), 0) AS existing_emi
FROM customers c
"""


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def to_record(row) -> dict:
    return {
        "id": row.id,
        "age": age_on(row.date_of_birth, datetime.now().astimezone().date()),
        "monthly_income": float(row.monthly_income),
        "credit_score": row.credit_score,
        "existing_emi": float(row.existing_emi),
    }


@pytest.fixture(scope="module")
def checksum_before():
    return table_checksum()


def table_checksum() -> tuple:
    with engine.connect() as conn:
        return tuple(
            conn.execute(
                text(
                    f"SELECT COUNT(*), md5(COALESCE(string_agg(t::text, ',' ORDER BY t.id), '')) "
                    f"FROM {table} t"
                )
            ).one()
            for table in ("customers", "loans")
        )


@pytest.fixture(scope="module")
def sampled(checksum_before):
    """N random rows plus the edge rows the spec asks for."""
    with engine.connect() as conn:
        rows = list(
            conn.execute(
                text(ROWS_SQL + " ORDER BY random() LIMIT :n"), {"n": SAMPLE_N}
            )
        )
        for order in [
            "c.credit_score ASC NULLS LAST",
            "existing_emi DESC",
            "c.date_of_birth ASC",
            "c.date_of_birth DESC",
        ]:
            rows += list(conn.execute(text(ROWS_SQL + f" ORDER BY {order} LIMIT 1")))
    unique = {row.id: row for row in rows}
    return [to_record(row) for row in unique.values()]


def test_lv0_connection_is_read_only():
    with engine.connect() as conn, pytest.raises(Exception, match="read-only"):
        conn.execute(text("UPDATE customers SET name = name WHERE false"))


def test_lv1_graph_matches_oracle(sampled, graph, run_case, fake_reader, thresholds):
    amount, tenure = thresholds["min_amount"] * 6, 36
    fake_reader(amount, tenure)
    mismatches = []
    for record in sampled:
        thread = f"live-{record['id']}"
        _, snapshot = run_case(graph, thread, record["id"])
        bot = "refer" if snapshot.interrupts else snapshot.values.get("decision")
        if record["credit_score"] is None:
            want = "need_info"
        else:
            want = oracle.expected_route(record, amount, tenure, thresholds)
        if bot != want:
            mismatches.append(
                f"id={record['id']} oracle={want} bot={bot} "
                f"failed={snapshot.values.get('failed_rules')}"
            )
    assert not mismatches, "LIVE mismatches:\n" + "\n".join(mismatches)


def test_lv2_data_quality():
    """Listed as DATA issues; this test never fails the bot for them."""
    checks = {
        "credit_score is NULL": "SELECT id FROM customers WHERE credit_score IS NULL",
        "income not positive": "SELECT id FROM customers WHERE monthly_income <= 0",
        "credit outside 300-900": "SELECT id FROM customers WHERE credit_score NOT BETWEEN 300 AND 900",
        "negative EMI": "SELECT customer_id FROM loans WHERE emi < 0",
        "duplicate email": "SELECT MIN(id) FROM customers GROUP BY lower(email) HAVING COUNT(*) > 1",
    }
    with engine.connect() as conn:
        issues = {
            name: [r[0] for r in conn.execute(text(sql))]
            for name, sql in checks.items()
        }
    for name, ids in issues.items():
        print(f"DATA: {name}: {len(ids)} row(s) {ids[:20]}")


def test_lv3_bot_reads_fresh_values(sampled):
    for record in sampled:
        found = get_customer.invoke({"customer_id": str(record["id"])})
        if record["credit_score"] is None:
            assert "no credit score" in found
            continue
        for field in ("age", "monthly_income", "credit_score", "existing_emi"):
            assert found[field] == record[field], f"id={record['id']} {field} differs"


def test_lv4_no_writes_happened(sampled, checksum_before):
    assert table_checksum() == checksum_before
