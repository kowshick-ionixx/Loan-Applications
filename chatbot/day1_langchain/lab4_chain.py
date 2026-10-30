from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

load_dotenv()
model = init_chat_model("ollama:qwen3.5:9b", reasoning=False, temperature=0)


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


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Extract the loan enquiry details from the customer's email. "
                "1 lakh = 100000 rupees, 'L' means lakh, 1 crore = 10000000 rupees. "
                "Indian digit grouping: 12,00,000 = 1200000. "
                "Convert years to months. If a detail is not stated, return null for it. "
                "Never guess."
            ),
        ),
        ("human", "{email}"),
    ]
)

extractor = model.with_structured_output(LoanEnquiry, method="function_calling")


chain = prompt | extractor

emails = [
    "Hi, I'm Ramesh Kumar. I need a loan of 5 lakh rupees for 3 years to renovate my house.",
    (
        "Hello team, this is Anita Sharma. Looking for Rs 12,00,000 personal loan, "
        "repayment over 60 months, for my sister's wedding."
    ),
    "need money urgently for my shop, around 2 lakhs, can repay in 18 months. - Imran",
]

results = chain.batch([{"email": e} for e in emails])

print(f"batch returned {len(results)} objects")
for r in results:
    print(type(r).__name__, r.model_dump())


print("\nStreaming:")
for chunk in model.stream("In two sentences, explain what an EMI is."):
    print(chunk.content, end="", flush=True)
print()
