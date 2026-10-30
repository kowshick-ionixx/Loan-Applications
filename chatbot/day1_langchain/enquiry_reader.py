from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

load_dotenv()

model = init_chat_model("ollama:qwen3.5:9b", reasoning=False, temperature=0)

ENQUIRIES_FILE = Path(__file__).resolve().parent.parent / "data" / "enquiries.txt"
RESULTS_FILE = Path(__file__).resolve().parent / "results.txt"
CORE_FIELDS = ["customer_name", "amount", "tenure_months", "purpose"]


class LoanEnquiry(BaseModel):
    customer_name: str | None = Field(
        None, description="Full name if stated, otherwise null"
    )
    amount: float | None = Field(
        None,
        description="Loan amount as a plain number of rupees, e.g. '5 lakh' -> 500000",
    )
    tenure_months: int | None = Field(
        None, description="Tenure converted to months, e.g. '3 years' -> 36"
    )
    purpose: str | None = Field(None, description="Why the loan is needed")
    confidence: Literal["high", "medium", "low"] = Field(
        description="high if every detail is clearly stated, medium if some are vague "
        "or missing, low if the text is barely a loan enquiry"
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Names of the fields above that were not stated in the email",
    )


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You read customer loan enquiry emails and extract the details.\n"
                "Rules:\n"
                "- NEVER guess. If a detail is not clearly stated, return null for it "
                "and list its field name in missing_fields.\n"
                "- Amounts are in rupees. 1 lakh = 100000, 'L' means lakh, "
                "1 crore = 10000000. Indian digit grouping: 12,00,000 = 1200000.\n"
                "- 'around 2 lakhs' still counts as stated: use 200000.\n"
                "- Convert tenure to months: 3 years = 36, 5 years = 60.\n"
                "- customer_name is the name the sender gives, even if only a first name.\n"
                "- Short forms count as stated. Example: 'Vikram here, car loan, 8L, 4 years' "
                "-> amount 800000, tenure_months 48, purpose 'car loan'."
            ),
        ),
        ("human", "{email}"),
    ]
)

chain = prompt | model.with_structured_output(LoanEnquiry, method="function_calling")


def could_not_read() -> LoanEnquiry:
    """The clean fallback result when an enquiry cannot be read."""
    return LoanEnquiry(confidence="low", missing_fields=list(CORE_FIELDS))


def read_enquiry(text: str) -> LoanEnquiry:
    """Read one enquiry email into a LoanEnquiry. One retry, then a clean fallback."""
    for attempt in (1, 2):
        try:
            if not text or not text.strip():
                raise ValueError("enquiry text is empty")
            result = chain.invoke({"email": text})

            result.missing_fields = [
                f for f in CORE_FIELDS if getattr(result, f) is None
            ]

            if result.missing_fields and result.confidence == "high":
                result.confidence = "medium"
            return result

        except Exception as exc:  # noqa: BLE001
            print(f"  attempt {attempt} failed: {exc}")
    return could_not_read()


def format_table(results: list[LoanEnquiry]) -> str:
    header = f"{'#':<3}{'Name':<16}{'Amount':>12}  {'Months':>6}  {'Purpose':<28}{'Conf':<8}Missing"
    lines = [header, "-" * len(header)]
    for i, r in enumerate(results, start=1):
        amount = f"{r.amount:,.0f}" if r.amount is not None else "-"
        months = str(r.tenure_months) if r.tenure_months is not None else "-"
        purpose = (r.purpose or "-")[:26]
        missing = ", ".join(r.missing_fields) or "-"
        lines.append(
            f"{i:<3}{r.customer_name or '-':<16}{amount:>12}  {months:>6}  "
            f"{purpose:<28}{r.confidence:<8}{missing}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    emails = [
        line.strip()
        for line in ENQUIRIES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    results = RunnableLambda(read_enquiry).batch(emails)

    table = format_table(results)
    print(table)

    print("\nEmpty string test:")
    empty = read_enquiry("")
    print(" ", empty.model_dump())

    RESULTS_FILE.write_text(
        table + "\n\nEmpty string -> " + str(empty.model_dump()) + "\n",
        encoding="utf-8",
    )
    print(f"Saved to {RESULTS_FILE.name}")

    for i in (0, 1):
        assert not results[
            i
        ].missing_fields, f"email {i + 1} should have every field filled"
    assert "amount" in results[3].missing_fields, "email 4 should be missing amount"
    assert (
        results[4].amount == 2_500_000
    ), f"25L should be 2,500,000, got {results[4].amount}"
    assert (
        results[4].tenure_months == 60
    ), f"5 years should be 60 months, got {results[4].tenure_months}"
    assert (
        results[3].confidence != "high"
    ), "email 4 has missing fields, so it can't be high confidence"
    assert (
        empty == could_not_read()
    ), "empty string should give the could-not-read result"
    print("\nAll asserts passed.")
