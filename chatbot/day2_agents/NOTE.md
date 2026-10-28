# What would break if the tool descriptions were vague?

1. The model never sees a tool's code, only its name, description and argument names, so those are its whole instruction manual.
2. In Lab 4, "does maths" still worked, but only because the argument names (`annual_rate_percent`, `tenure_months`) still explained the units.
3. With vague names as well, the model could send 0.11 instead of 11, or 3 (years) instead of 36 (months), and every EMI would be wrong.
4. With three tools, it could pick the wrong one, skip a tool and guess the number itself, or answer an eligibility question without checking.
5. The order would break too: `check_eligibility` needs `new_emi` from `emi_calculator`, and only the descriptions tell the model to get the customer and the EMI first.
