from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage
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


# function_calling: this local model drops values with the default json_schema method
extractor = model.with_structured_output(LoanEnquiry, method="function_calling")

# The system message tells the model its job; without it, it doesn't know to extract
instructions = SystemMessage(
    "Extract the loan enquiry details from the customer's email. "
    "1 lakh = 100000 rupees, 'L' means lakh, 1 crore = 10000000 rupees. "
    "Convert years to months. If a detail is not stated, return null for it. Never guess."
)

email = "Hi, I'm Ramesh Kumar. I need a loan of 5 lakh rupees for 3 years to renovate my house."
result = extractor.invoke([instructions, HumanMessage(email)])

print(type(result))
print(result)
if result.amount is not None:
    print("Amount + 1 =", result.amount + 1)  # proves it's a real number, not text

# A vague email: the missing boxes should come back as None
vague = extractor.invoke(
    [
        instructions,
        HumanMessage(
            "Good morning, I want a loan for a two-wheeler. My name is Priya."
        ),
    ]
)
print(vague.model_dump())
