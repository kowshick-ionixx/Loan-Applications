from langchain.tools import tool


@tool
def emi_calculator(
    principal: float, annual_rate_percent: float, tenure_months: int
) -> float:
    """Calculate the monthly EMI of a loan.
    principal is in rupees, annual_rate_percent is like 11 for 11 percent,
    tenure_months is the loan length in months."""
    r = annual_rate_percent / (12 * 100)  # yearly percent -> monthly decimal
    factor = (1 + r) ** tenure_months
    return round(principal * r * factor / (factor - 1), 2)


# This is all the model ever sees of the tool: not the code, just these three
print("Name:       ", emi_calculator.name)
print("Description:", emi_calculator.description)
print("Args:       ", emi_calculator.args)

# Call the tool directly, no AI involved: 5 lakh at 11% for 3 years
emi = emi_calculator.invoke(
    {"principal": 500000, "annual_rate_percent": 11, "tenure_months": 36}
)
print("\nEMI for 5,00,000 at 11% for 36 months:", emi)

assert abs(emi - 16370) < 5, f"guide says about 16,370, got {emi}"
print("Assert passed.")
