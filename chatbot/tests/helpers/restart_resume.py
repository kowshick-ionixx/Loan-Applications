"""Process 2 of the restart test: resume a paused case from the same file.

usage: restart_resume.py DB_FILE THREAD_ID DECISION
Prints the final decision and log as JSON; exit code 1 if nothing was waiting.
"""

import argparse
import json
import sys
from pathlib import Path

import _paths  # noqa: F401

parser = argparse.ArgumentParser()
parser.add_argument("db_file")
parser.add_argument("thread_id")
parser.add_argument("decision")
args = parser.parse_args()

import cases
from approval_graph import sqlite_graph

graph = sqlite_graph(Path(args.db_file))
try:
    values = cases.decide(graph, args.thread_id, args.decision, "restart-test")
except ValueError as exc:
    print(json.dumps({"error": str(exc)}))
    sys.exit(1)
finally:
    graph.checkpointer.conn.close()
print(json.dumps({"decision": values["decision"], "log": values["log"]}))
