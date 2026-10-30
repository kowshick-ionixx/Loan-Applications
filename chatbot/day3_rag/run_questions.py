from pathlib import Path

from policy_qa import ask_policy

ANSWERS_FILE = Path(__file__).resolve().parent / "answers.md"

QUESTIONS = [
    "What is the minimum age?",
    "What happens if my credit score is 680?",
    "What is the processing fee on a 6,00,000 loan?",
    "Can I prepay after 8 months?",
    "What income proof does a self-employed applicant need?",
    "Who approves a 12,00,000 loan?",
    "How long until disbursal?",
    "Can the money go to my friend's account?",
    "What is the policy on gold loans?",
    "What interest rate will I get with a 750 score?",
]


def clean(text: str) -> str:
    """Make text safe for one Markdown table cell."""
    return text.replace("|", "/").replace("\n", " ")


lines = [
    "# Policy Q&A results",
    "",
    "| # | Question | Answer | Sections |",
    "|---|----------|--------|----------|",
]

for i, question in enumerate(QUESTIONS, start=1):
    result = ask_policy(question)
    sections = ", ".join(result.sections) if result.sections else "—"

    print(f"Q{i}: {question}")
    print(f"    Answer:   {result.answer}")
    print(f"    Sections: {sections}")
    print()

    lines.append(f"| {i} | {clean(question)} | {clean(result.answer)} | {sections} |")

ANSWERS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Saved to {ANSWERS_FILE}")
