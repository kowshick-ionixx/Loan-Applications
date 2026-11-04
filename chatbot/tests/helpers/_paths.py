"""Put the day folders on sys.path, as conftest does. DATABASE_URL comes from
the parent test process's environment (the isolated test database)."""

import sys
from pathlib import Path

CHATBOT = Path(__file__).resolve().parents[2]
for folder in [
    "day1_langchain",
    "day2_agents",
    "day3_rag",
    "day4_langgraph",
    "day5_capstone",
]:
    sys.path.insert(0, str(CHATBOT / folder))
