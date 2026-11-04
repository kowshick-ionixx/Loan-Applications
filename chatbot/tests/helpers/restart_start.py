"""Process 1 of the restart test: run a case until it pauses, then exit.

usage: restart_start.py DB_FILE THREAD_ID CUSTOMER_ID [--amount A --tenure T] [--email TEXT]
With --amount/--tenure the model in intake is replaced by that fixed enquiry;
with only --email the real model reads the message.
"""

import argparse
import json
from pathlib import Path

import _paths  # noqa: F401

parser = argparse.ArgumentParser()
parser.add_argument("db_file")
parser.add_argument("thread_id")
parser.add_argument("customer_id")
parser.add_argument("--amount", type=float)
parser.add_argument("--tenure", type=int)
parser.add_argument("--email", default="(restart test)")
args = parser.parse_args()

import cases
import nodes
from approval_graph import sqlite_graph
from enquiry_reader import LoanEnquiry

if args.amount is not None:
    enquiry = LoanEnquiry(
        amount=args.amount, tenure_months=args.tenure, purpose="test", confidence="high"
    )
    nodes.read_enquiry = lambda text: enquiry

graph = sqlite_graph(Path(args.db_file))
events = list(cases.stream_case(graph, args.thread_id, args.customer_id, args.email))
snapshot = graph.get_state(cases.thread_config(args.thread_id))
graph.checkpointer.conn.close()
print(json.dumps({"nodes": [node for node, _ in events], "next": list(snapshot.next)}))
